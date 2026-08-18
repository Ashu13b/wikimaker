"""Tag each source as reliable_secondary / primary / self_published / unreliable."""
from __future__ import annotations
import json
from .models import Source, SourceReliability
from .llm import LLMProvider

from .publishers import (
    INDEPENDENT_NEWS_DOMAINS,
    ACADEMIC_PUBLISHER_DOMAINS,
    PRIMARY_OR_INSTITUTIONAL_DOMAINS,
    SELF_PUBLISHED_DOMAINS,
    UNRELIABLE_DOMAINS,
)

# Known reliable secondary source domains — skip LLM for these
_RS_DOMAINS = INDEPENDENT_NEWS_DOMAINS | ACADEMIC_PUBLISHER_DOMAINS | {
    "en.wikipedia.org", "wikipedia.org", "britannica.com", "sgttimes.com",
}
_PRIMARY_DOMAINS = PRIMARY_OR_INSTITUTIONAL_DOMAINS
_SELF_DOMAINS = SELF_PUBLISHED_DOMAINS
_UNRELIABLE_DOMAINS = UNRELIABLE_DOMAINS


def _domain_classify(url: str) -> SourceReliability | None:
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().replace("www.", "")
    for d in _RS_DOMAINS:
        if host == d or host.endswith("." + d):
            return SourceReliability.reliable_secondary
    for d in _UNRELIABLE_DOMAINS:
        if host == d or host.endswith("." + d):
            return SourceReliability.unreliable
    for d in _SELF_DOMAINS:
        if host == d or host.endswith("." + d):
            return SourceReliability.self_published
    for d in _PRIMARY_DOMAINS:
        if host == d or host.endswith("." + d):
            return SourceReliability.primary
    return None


SYSTEM = """\
You are a Wikipedia source reliability classifier following WP:RS policy.
Classify each source into exactly one category:
- reliable_secondary: Independent journalism (Reuters, AP, major newspapers, magazines), peer-reviewed journals, books from major publishers, university press, government/institutional publications
- primary: The subject's official pages, university profile, institutional bio, their own published papers (counts as primary for the person, not the work)
- self_published: Personal website, blog, LinkedIn, ResearchGate profile, social media, the subject's own writing about themselves
- unreliable: Content farms, tabloids, wikis, IMDb, Fandom, aggregators, predatory journals

Respond with JSON only: {"reliability": "<category>", "reason": "<one line>"}"""


def classify_sources(sources: list[Source], llm: LLMProvider) -> list[Source]:
    for source in sources:
        # Domain-based fast path — no LLM needed
        domain_tag = _domain_classify(source.url)
        if domain_tag is not None:
            source.reliability = domain_tag
            continue
        if source.reliability == SourceReliability.reliable_secondary:
            continue  # already tagged by Semantic Scholar — trust it
        # Fall back to LLM for unknown domains
        prompt = f"URL: {source.url}\nTitle: {source.title}\nPublisher: {source.publisher}\nSnippet: {source.snippet[:200]}"
        try:
            raw = llm.complete(SYSTEM, prompt)
            data = json.loads(raw)
            source.reliability = SourceReliability(data["reliability"])
        except Exception:
            pass
    return sources
