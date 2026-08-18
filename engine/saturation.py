"""Research Saturation & Fact Repetition Analytics.

Detects when web searches and claim extraction have reached saturation
(diminishing returns where newly discovered links and queries repeat
already-known facts and syndicated wire reports).
"""
from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urlsplit
from typing import Sequence

from .models import Claim, PersonProfile, ClaimCluster, ResearchSaturation


_STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "of", "to", "for", "with", "by", "from",
    "and", "or", "as", "is", "was", "were", "are", "be", "been", "being", "have",
    "has", "had", "dr", "prof", "mr", "mrs", "ms", "under", "led", "team", "first",
    "also", "which", "that", "this", "these", "those", "about", "after", "before",
}

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase alphanumeric words excluding basic stopwords."""
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def _ngrams(tokens: list[str], n: int = 2) -> set[str]:
    """Generate word n-grams."""
    if len(tokens) < n:
        return set()
    return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def calculate_claim_similarity(claim_a: Claim, claim_b: Claim) -> float:
    """Calculate semantic and factual similarity between two claims (0.0 to 1.0)."""
    text_a = claim_a.text.lower()
    text_b = claim_b.text.lower()

    if text_a == text_b:
        return 1.0

    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    # Token Jaccard & Containment overlap
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    token_jaccard = len(intersection) / len(union) if union else 0.0
    min_len = min(len(tokens_a), len(tokens_b))
    containment = len(intersection) / min_len if min_len else 0.0

    # Year alignment bonus / penalty
    years_a = set(_YEAR_RE.findall(text_a))
    years_b = set(_YEAR_RE.findall(text_b))
    year_score = 0.0
    if years_a and years_b:
        if years_a & years_b:
            year_score = 0.20
        else:
            # Different explicit years -> likely distinct events
            year_score = -0.35

    # Bigram overlap for phrasal alignment
    words_list_a = [w for w in _WORD_RE.findall(text_a) if w not in _STOPWORDS]
    words_list_b = [w for w in _WORD_RE.findall(text_b) if w not in _STOPWORDS]
    bigrams_a = _ngrams(words_list_a, 2)
    bigrams_b = _ngrams(words_list_b, 2)
    bigram_jaccard = 0.0
    if bigrams_a and bigrams_b:
        bigram_jaccard = len(bigrams_a & bigrams_b) / len(bigrams_a | bigrams_b)

    # Field match bonus
    field_bonus = 0.15 if (claim_a.field and claim_a.field == claim_b.field) else 0.0

    combined = (0.35 * token_jaccard) + (0.25 * containment) + (0.15 * bigram_jaccard) + year_score + field_bonus
    return max(0.0, min(1.0, combined))


def cluster_claims(claims: Sequence[Claim]) -> list[ClaimCluster]:
    """Group semantically redundant or corroborating claims into clusters."""
    if not claims:
        return []

    clusters: list[list[int]] = [] # list of lists of claim indices
    assigned = [False] * len(claims)

    for i, claim in enumerate(claims):
        if assigned[i]:
            continue
        current_cluster = [i]
        assigned[i] = True

        for j in range(i + 1, len(claims)):
            if assigned[j]:
                continue
            sim = calculate_claim_similarity(claim, claims[j])
            if sim >= 0.48:
                current_cluster.append(j)
                assigned[j] = True

        clusters.append(current_cluster)

    result: list[ClaimCluster] = []
    for cluster_indices in clusters:
        cluster_claims_list = [claims[idx] for idx in cluster_indices]
        # Pick the most complete / informative text as canonical
        canonical = max(cluster_claims_list, key=lambda c: len(c.text))
        urls = {c.source_url for c in cluster_claims_list if c.source_url}

        result.append(
            ClaimCluster(
                canonical_text=canonical.draft_text or canonical.text,
                field=canonical.field,
                corroborating_sources=sorted(urls),
                claim_indices=cluster_indices,
                repetition_count=len(cluster_indices),
            )
        )

    return result


def analyze_research_saturation(profile: PersonProfile) -> ResearchSaturation:
    """Analyze source breadth, fact repetition, and syndication to produce a saturation score."""
    claims = profile.claims
    sources = profile.sources

    if not claims and not sources:
        return ResearchSaturation(
            score=0.0,
            level="exploring",
            repetition_rate=0.0,
            syndication_rate=0.0,
            unique_fact_count=0,
            total_claims_analyzed=0,
            summary="Research has just begun. Discover and verify sources to build the profile.",
            corroborated_clusters=[],
        )

    clusters = cluster_claims(claims)
    total_claims = len(claims)
    unique_facts = len(clusters)

    repetition_rate = (
        round((total_claims - unique_facts) / total_claims, 2)
        if total_claims > 0 else 0.0
    )

    # Syndication analysis: sources sharing editorial origins or hostnames
    origins: dict[str, int] = defaultdict(int)
    for s in sources:
        if s.editorial_origin:
            origins[s.editorial_origin.lower().strip()] += 1
        elif s.url:
            host = (urlsplit(s.url).hostname or "").lower().removeprefix("www.")
            if host:
                origins[host] += 1

    syndicated_source_count = sum(count - 1 for count in origins.values() if count > 1)
    syndication_rate = (
        round(syndicated_source_count / len(sources), 2)
        if sources else 0.0
    )

    # Multi-component saturation calculation:
    # 1. Source breadth: up to 15 sources = 0.35
    source_breadth_score = min(len(sources) / 15.0, 1.0) * 0.35

    # 2. Fact repetition: repetition_rate * 0.35 (facts repeating = saturation)
    repetition_score = min(repetition_rate * 1.5, 1.0) * 0.35

    # 3. Missing slot coverage: 0.20 for completing key slots (birth, affiliation, career, awards)
    missing_count = len(profile.missing_slots or [])
    slot_score = max(0.0, (1.0 - (missing_count / 6.0))) * 0.20

    # 4. Syndication signal: 0.10 for high media syndication
    syndication_score = min(syndication_rate * 1.5, 1.0) * 0.10

    total_score = round(min(1.0, source_breadth_score + repetition_score + slot_score + syndication_score), 2)

    if total_score >= 0.75 or (len(sources) >= 12 and repetition_rate >= 0.35):
        level = "saturated"
        summary = (
            f"Research saturated ({int(total_score * 100)}%). Key facts are corroborating across "
            f"{len(sources)} sources with {len(clusters)} distinct fact clusters. "
            "Public web record is well-captured; diminishing returns on further searching."
        )
    elif total_score >= 0.45:
        level = "mature"
        summary = (
            f"Mature research ({int(total_score * 100)}%). Core milestones identified, "
            f"with {len(clusters)} unique facts. Some minor slots or secondary reports may remain."
        )
    else:
        level = "exploring"
        summary = (
            f"Active discovery ({int(total_score * 100)}%). New queries and sweeps are still yielding "
            "novel facts and unvisited sources."
        )

    # Filter corroborated clusters (clusters with > 1 corroborating source or repeated claims)
    corroborated = [c for c in clusters if c.repetition_count > 1 or len(c.corroborating_sources) > 1]
    corroborated.sort(key=lambda c: (len(c.corroborating_sources), c.repetition_count), reverse=True)

    return ResearchSaturation(
        score=total_score,
        level=level,
        repetition_rate=repetition_rate,
        syndication_rate=syndication_rate,
        unique_fact_count=unique_facts,
        total_claims_analyzed=total_claims,
        summary=summary,
        corroborated_clusters=corroborated,
    )
