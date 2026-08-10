"""Notability scoring — informational only, never blocks draft generation."""
from __future__ import annotations
import time
import requests
from .models import Source, SourceReliability, NotabilityResult
from .provenance import classify_source_provenance

S2_API = "https://api.semanticscholar.org/graph/v1"

# Semantic Scholar is rate-limited (unauthenticated ~100 req/5min); notability is
# recomputed on every session save, so cache per-name rather than hammering it.
_S2_TTL_SECONDS = 600
_s2_cache: dict[str, tuple[float, dict]] = {}


def score_notability(name: str, sources: list[Source], claims: list | None = None) -> NotabilityResult:
    """Return a conservative coverage signal, never an acceptance prediction.

    A source counts only when it is independent secondary coverage, has been
    human-verified, and supports a confirmed claim. Count distinct outlets as
    a conservative proxy for editorial independence. Only sources a human has
    marked as significant coverage affect the score; editorial-origin labels
    let syndicated copies collapse into a single origin.
    """
    from urllib.parse import urlsplit
    from .models import VerificationState
    from .provenance import normalize_url

    classified_sources = [classify_source_provenance(s, name) for s in sources]
    confirmed_urls = {
        normalize_url(claim.source_url)
        for claim in (claims or [])
        if claim.source_url
        and claim.verification in {VerificationState.confirmed, VerificationState.edited}
    }
    candidates = [
        source for source in classified_sources
        if normalize_url(source.url) in confirmed_urls
        and source.human_verified
        and source.is_independent
        and source.provenance_category == "independent_secondary"
        and source.reliability == SourceReliability.reliable_secondary
        and source.relevance_flag != "likely_wrong"
    ]

    def editorial_key(source: Source) -> str:
        explicit = (source.editorial_origin or "").strip().lower()
        return explicit or (urlsplit(source.url).hostname or "").lower().removeprefix("www.")

    candidate_outlets = {editorial_key(source) for source in candidates}
    candidate_outlets.discard("")
    outlets = {editorial_key(source) for source in candidates if source.coverage_depth == "significant"}
    outlets.discard("")
    rs_count = len(outlets)
    candidate_count = len(candidate_outlets)

    # Authored works remain useful identity/research context, but publication
    # volume does not itself satisfy academic notability and adds no score.
    authored_count = sum(
        1 for source in classified_sources
        if source.provenance_category == "authored_publication"
        and normalize_url(source.url) in confirmed_urls
    )
    wp_prof_signals = (
        [f"{authored_count} confirmed authored publications (context only; not a notability criterion)"]
        if authored_count else []
    )

    score = round(min(rs_count / 3, 1.0), 2)
    if score >= 0.8:
        label = "Strong coverage"
        reason = (
            f"{rs_count} distinct editorial origins have significant person-focused coverage. "
            "A human must still assess significant coverage or an academic-notability criterion."
        )
    elif score >= 0.5:
        label = "Moderate coverage"
        reason = (
            f"{rs_count} distinct editorial origin(s) have significant person-focused coverage. "
            "Seek deeper person-focused coverage or a clearly documented academic-notability criterion."
        )
    elif score >= 0.2:
        label = "Weak coverage"
        reason = f"Only {rs_count} distinct editorial origin has been assessed as significant coverage."
    elif candidate_count:
        label = "Coverage needs review"
        reason = (
            f"{candidate_count} independent outlet(s) support confirmed claims, but none has been "
            "assessed as significant person-focused coverage."
        )
    else:
        label = "Insufficient coverage"
        reason = "No independent outlet currently supports a confirmed claim."

    return NotabilityResult(
        score=score,
        label=label,
        rs_count=rs_count,
        reason=reason,
        candidate_count=candidate_count,
        wp_prof_signals=wp_prof_signals,
    )


def _semantic_scholar_signals(name: str) -> dict:
    now = time.time()
    cached = _s2_cache.get(name)
    if cached and now - cached[0] < _S2_TTL_SECONDS:
        return cached[1]
    result = _fetch_semantic_scholar(name)
    _s2_cache[name] = (now, result)
    return result


def _fetch_semantic_scholar(name: str) -> dict:
    try:
        resp = requests.get(f"{S2_API}/author/search",
            params={"query": name, "fields": "citationCount,paperCount,hIndex", "limit": 1},
            timeout=8)
        resp.raise_for_status()
        authors = resp.json().get("data", [])
        if not authors:
            return {}
        a = authors[0]
        return {
            "citation_count": a.get("citationCount", 0),
            "paper_count": a.get("paperCount", 0),
            "h_index": a.get("hIndex", 0),
        }
    except Exception:
        return {}
