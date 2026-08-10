"""Compare session claims against a live Wikipedia article (existing-article mode).

Deterministic, no LLM: token-overlap matching against the article's plain text.
`covered` means the fact's wording already appears in the article; anything not
covered becomes a candidate addition in the edit proposal. The split is a
heuristic aid for the human editor, never a machine judgment.
"""
from __future__ import annotations

import re
from typing import Optional

import requests
from pydantic import BaseModel

from engine.models import PersonProfile, Claim

WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)"}

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "at",
    "by", "from", "as", "is", "was", "were", "are", "has", "have", "had", "he",
    "she", "his", "her", "their", "its", "this", "that", "who", "which", "while",
    "during", "also", "into", "about", "after", "before", "among", "between",
}

_COVERAGE_THRESHOLD = 0.6


class ClaimCoverage(BaseModel):
    claim_index: int
    field: str
    text: str
    date_context: Optional[str] = None
    source_url: Optional[str] = None
    covered: bool
    score: float
    note: str


class ArticleProposal(BaseModel):
    article_title: str
    article_url: str
    article_excerpt: str = ""
    covered_count: int
    missing_count: int
    coverage: list[ClaimCoverage]


def title_from_url(url: str) -> str:
    m = re.search(r"/wiki/([^/?#]+)", url)
    if not m:
        raise ValueError(f"Not a Wikipedia article URL: {url}")
    return m.group(1).replace("_", " ")


def fetch_article_text(title: str) -> str:
    """Plain-text extract of the live article (TextExtracts, then wikitext fallback)."""
    try:
        resp = requests.get(WIKI_API, params={
            "action": "query", "prop": "extracts", "explaintext": "1",
            "titles": title, "format": "json",
        }, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            extract = page.get("extract")
            if extract:
                return extract
    except Exception:
        pass
    resp = requests.get(WIKI_API, params={
        "action": "parse", "page": title, "prop": "wikitext", "format": "json",
    }, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json().get("parse", {}).get("wikitext", {}).get("*", "")


def _tokens(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9]+", text.lower())
        if t not in STOPWORDS and len(t) > 2
    }


def claim_coverage(claim: Claim, article_text: str) -> ClaimCoverage:
    article_tokens = _tokens(article_text)
    claim_tokens = _tokens(claim.text)
    score = len(claim_tokens & article_tokens) / len(claim_tokens) if claim_tokens else 0.0

    # A verbatim year in the source that is absent from the article weakens coverage
    # for temporal facts even when generic tokens overlap.
    year_in_claim = re.search(r"\b(1[89]\d\d|20\d\d)\b", claim.date_context or "")
    if year_in_claim and year_in_claim.group(1) not in article_text:
        score = min(score, score * 0.5)

    covered = score >= _COVERAGE_THRESHOLD
    note = (
        "Fact wording already appears in the article."
        if covered else
        "Not found in the article — candidate addition."
    )
    return ClaimCoverage(
        claim_index=-1,  # filled by caller
        field=claim.field,
        text=claim.text,
        date_context=claim.date_context,
        source_url=claim.source_url,
        covered=covered,
        score=round(score, 2),
        note=note,
    )


def build_article_proposal(profile: PersonProfile, title: str, url: str, article_text: str) -> ArticleProposal:
    candidates = [
        c for c in profile.claims
        if c.verification.value in ("confirmed", "edited")
    ]
    coverage: list[ClaimCoverage] = []
    for i, claim in enumerate(candidates):
        row = claim_coverage(claim, article_text)
        row.claim_index = i
        coverage.append(row)

    covered = [c for c in coverage if c.covered]
    missing = [c for c in coverage if not c.covered]
    return ArticleProposal(
        article_title=title,
        article_url=url,
        article_excerpt=article_text[:400],
        covered_count=len(covered),
        missing_count=len(missing),
        coverage=coverage,
    )
