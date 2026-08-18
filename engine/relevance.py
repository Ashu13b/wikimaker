"""Score web/news sources for relevance to a specific person.

Academic DOI sources are validated by author_check; this module handles
web, news, and profile sources where we only have a snippet and title.
"""
from __future__ import annotations
from .models import Source

# Fields that strongly indicate a different well-known person with the same name
_WRONG_PERSON_SIGNALS = [
    "politician", "member of parliament", "member of legislative", "lok sabha", "vidhan sabha",
    "elections", "candidate", "constituency", "polling", "party", "bjp", "inc", "bsp", "samajwadi",
    "actor", "actress", "singer", "musician", "spotify", "deezer", "soundcloud", "album", "artist",
    "cricketer", "footballer", "minister", "chief minister", "governor", "judge", "justice",
    "director general", "inspector general", "police", "honda", "sales executive", "tutor", "urbanpro",
]

_ACADEMIC_FETCHED_BY = {"semantic_scholar"}
_DOI_PATTERNS = ["doi.org", "pubmed", "ncbi.nlm", "springer", "plos",
                 "tandfonline", "wiley", "elsevier", "mdpi", "frontiersin"]

# Domains that exist to redirect elsewhere — a final URL on a different domain
# is the expected outcome, not a wrong-page trap.
_SHORTENERS = {"t.co", "bit.ly", "goo.gl", "tinyurl.com", "ow.ly", "bit.do",
               "rb.gy", "dlvr.it", "trib.al", "lnkd.in", "shorturl.at", "rebrand.ly"}


_PRESENTATION_SUBDOMAINS = ("www.", "m.", "mobile.", "amp.")


def _redirect_norm(url: str) -> tuple[str, str]:
    from urllib.parse import urlparse
    p = urlparse(url)
    host = p.netloc.lower()
    for prefix in _PRESENTATION_SUBDOMAINS:
        if host.startswith(prefix):
            host = host[len(prefix):]
            break
    path = p.path.rstrip("/") or "/"
    # AMP pages are the same article; normalize the /amp suffix away.
    if path.endswith("/amp"):
        path = path[: -len("/amp")] or "/"
    return host, path


def is_meaningful_redirect(url: str, final_url: str) -> bool:
    """True when a fetch landed on a materially different page than requested.

    Catches silent same-site redirects to an unrelated article (e.g. a jagran
    URL that now serves a different article). Ignores scheme/host-normalisation,
    AMP variants, URL shorteners, and DOI resolvers (those legitimately redirect
    to publishers).
    """
    if not final_url or final_url == url:
        return False
    ohost, opath = _redirect_norm(url)
    fhost, fpath = _redirect_norm(final_url)
    if ohost in _SHORTENERS or fhost in _SHORTENERS:
        return False
    if any(d in url.lower() for d in _DOI_PATTERNS):
        return False
    if ohost != fhost:
        return True
    return opath != fpath


_INDIC_NAME_MAP = {
    "prem": "प्रेम", "singh": "सिंह", "yadav": "यादव", "kumar": "कुमार",
    "sharma": "शर्मा", "verma": "वर्मा", "gupta": "गुप्ता", "lal": "लाल",
    "rao": "राव", "reddy": "रेड्डी", "patel": "पटेल", "mishra": "मिश्रा",
    "joshi": "जोशी", "nair": "नायर", "das": "दास", "sen": "सेन",
}

_INDIC_CONTEXT_TERMS = [
    "वैज्ञानिक", "अनुसंधान", "शोध", "संस्थान", "क्लोन", "क्लोनिंग", "हिसार", "सीआईआरबी",
    "कृषि", "बायोटेक्नोलॉजी", "बायो", "प्रोफेसर", "डॉक्टर", "डॉ.", "गौरव", "मुर्रा",
]


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

    full_text = (url_lower + " " + source.snippet + " " + source.title).lower()
    if not full_text.strip():
        return "unscored"

    name_tokens = _significant_name_tokens(person_name)
    field_tokens = [t.lower() for t in (field or "").split() if len(t) > 3]
    affil_tokens = [t.lower() for t in (affiliation or "").split() if len(t) > 3]
    context_tokens = field_tokens + affil_tokens

    # Check English name tokens or vernacular Devanagari transliterated tokens
    indic_tokens = [_INDIC_NAME_MAP[t] for t in name_tokens if t in _INDIC_NAME_MAP]
    name_found = all(t in full_text for t in name_tokens) or (
        bool(indic_tokens) and all(t in full_text for t in indic_tokens)
    )

    # Check for wrong-person signals in URL or snippet text
    for signal in _WRONG_PERSON_SIGNALS:
        if signal in full_text:
            if not any(t in full_text for t in context_tokens):
                return "likely_wrong"

    all_context = context_tokens + _INDIC_CONTEXT_TERMS
    if name_found and all_context and any(t in full_text for t in all_context):
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
