"""Score web/news sources for relevance to a specific person.

Academic DOI sources are validated by author_check; this module handles
web, news, and profile sources where we only have a snippet and title.
"""
from __future__ import annotations
import re
from .models import Source

# Fields that strongly indicate a different well-known person with the same name
_WRONG_PERSON_SIGNALS = [
    "politician", "member of parliament", "member of legislative",
    "actor", "actress", "singer", "musician", "cricketer", "footballer",
    "minister", "chief minister", "governor", "judge", "justice",
    "director general", "inspector general", "police",
]

_ACADEMIC_FETCHED_BY = {"semantic_scholar"}
_DOI_PATTERNS = ["doi.org", "pubmed", "ncbi.nlm", "springer", "plos",
                 "tandfonline", "wiley", "elsevier", "mdpi", "frontiersin"]


def _significant_name_tokens(name: str) -> list[str]:
    skip = {"dr", "dr.", "prof", "prof.", "mr", "mrs", "ms", "shri", "smt"}
    return [t.lower() for t in name.split() if len(t) > 2 and t.lower() not in skip]


def flag_source(source: Source, person_name: str, field: str, affiliation: str) -> str:
    """Return relevance_flag for a single source.

    Skips DOI/academic sources (author_check handles those).
    Returns: "relevant" | "uncertain" | "likely_wrong" | "unscored"
    """
    # DOI / Semantic Scholar sources: already validated by author_check
    if source.fetched_by in _ACADEMIC_FETCHED_BY:
        return "unscored"
    url_lower = source.url.lower()
    if any(d in url_lower for d in _DOI_PATTERNS):
        return "unscored"
    # No snippet to check
    text = (source.snippet + " " + source.title).lower()
    if not text.strip():
        return "unscored"

    name_tokens = _significant_name_tokens(person_name)
    field_tokens = [t.lower() for t in (field or "").split() if len(t) > 3]
    affil_tokens = [t.lower() for t in (affiliation or "").split() if len(t) > 3]
    context_tokens = field_tokens + affil_tokens

    name_found = all(t in text for t in name_tokens)

    # Check for wrong-person signals before anything else
    if name_found:
        for signal in _WRONG_PERSON_SIGNALS:
            if signal in text:
                # Only flag if NONE of the expected context tokens appear
                if not any(t in text for t in context_tokens):
                    return "likely_wrong"

    if name_found and context_tokens and any(t in text for t in context_tokens):
        return "relevant"
    if name_found:
        return "uncertain"  # name present but no field/affiliation context
    return "uncertain"      # name not found in snippet (could still be right page)


def flag_sources(
    sources: list[Source],
    person_name: str,
    field: str | None,
    affiliation: str | None,
) -> list[Source]:
    """Flag all sources in-place and return the list."""
    f = field or ""
    a = affiliation or ""
    for s in sources:
        if s.relevance_flag == "unscored":
            s.relevance_flag = flag_source(s, person_name, f, a)
    return sources
