"""Goal-directed URL suggestion engine.

Suggestion queue is fed from two sources:
1. Profile links extracted from already-fetched pages (high priority — warm leads)
2. LLM-generated web searches anchored to affiliation + field (fallback)

Each suggestion carries: fetchable, relevance, completion_value.
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from .models import PersonProfile

# ── Slot priority weights ──────────────────────────────────────────────────────
_SLOT_PRIORITY: dict[str, int] = {
    "birth_date": 3, "known_for": 3, "award": 3,
    "affiliation": 2, "position": 2, "education": 2,
    "field": 1, "nationality": 1, "full_name": 1, "birth_place": 1,
}

# ── Fetchability — domain-based, no extra network call ────────────────────────
_PAYWALLED = {
    "sciencedirect.com", "scopus.com", "springer.com", "nature.com",
    "wiley.com", "tandfonline.com", "jstor.org", "elsevier.com",
}
_NEEDS_BROWSER = {
    "researchgate.net", "linkedin.com", "x.com", "twitter.com",
}

def _fetchability(url: str) -> str:
    domain = urlparse(url).netloc.lower().replace("www.", "")
    for d in _PAYWALLED:
        if domain == d or domain.endswith("." + d):
            return "paywalled"
    for d in _NEEDS_BROWSER:
        if domain == d or domain.endswith("." + d):
            return "needs_browser"
    return "open"


def is_profile_url(url: str) -> bool:
    url_lower = url.lower()
    # Check known profile domains
    profile_domains = [
        "orcid.org", "scholar.google.", "researchgate.net/profile",
        "scopus.com/authid", "linkedin.com", "semanticscholar.org/author",
        "academia.edu", "loop.frontiersin.org", "publons.com", "openalex.org/authors"
    ]
    if any(d in url_lower for d in profile_domains):
        return True
    # Check institutional profile paths
    profile_paths = ["/faculty/", "/staff/", "/people/", "/profile/", "/researcher/", "/person/", "/member/"]
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        if any(d in domain for d in ["edu", "ac.in", "res.in", "gov"]):
            if any(p in path for p in profile_paths):
                return True
    except Exception:
        pass
    return False


def _classify_source_type(url: str, title: str = "") -> str:
    """Classify a suggestion URL into profile / publication / news."""
    url_lower = url.lower()
    # Academic / publication domains
    pub_domains = [
        "doi.org", "pubmed", "ncbi.nlm", "springer.com", "nature.com",
        "wiley.com", "tandfonline.com", "elsevier.com", "sciencedirect.com",
        "mdpi.com", "frontiersin.org", "plos", "jstor.org", "hindawi.com",
        "semanticscholar.org/paper", "arxiv.org",
    ]
    if any(d in url_lower for d in pub_domains):
        return "publication"
    # ResearchGate publication pages
    if "researchgate.net/publication" in url_lower:
        return "publication"
    # Profile check (redundant but safe)
    if is_profile_url(url):
        return "profile"
    # News heuristics
    news_domains = [
        "thehindu.com", "ndtv.com", "timesofindia", "hindustantimes",
        "indianexpress", "livemint", "scroll.in", "thewire.in",
        "news18.com", "bbc.com", "reuters.com",
    ]
    if any(d in url_lower for d in news_domains):
        return "news"
    return "news"  # default bucket


# ── Relevance — how likely this result is about the right person ───────────────
def _relevance(title: str, snippet: str, affil: str, field: str, claims: list) -> str:
    haystack = (title + " " + snippet).lower()
    anchors: list[str] = []
    if affil:
        anchors.extend(w.lower() for w in affil.split() if len(w) > 3)
    if field:
        anchors.extend(w.lower() for w in field.split() if len(w) > 3)
    for c in claims[:8]:
        anchors.extend(w.lower() for w in c.text.split() if len(w) > 5)
    if not anchors:
        return "medium"
    hits = sum(1 for a in set(anchors) if a in haystack)
    ratio = hits / len(set(anchors))
    if ratio > 0.12:
        return "high"
    if ratio > 0.04:
        return "medium"
    return "low"


# ── Completion value — weighted sum of missing slots this might fill ───────────
def _completion_value(expected_slots: list[str], missing: list[str]) -> int:
    missing_set = set(missing)
    return sum(_SLOT_PRIORITY.get(s, 1) for s in expected_slots if s in missing_set)


# ── Gap detection ─────────────────────────────────────────────────────────────

def _extract_first_year(s: str | None) -> int | None:
    if not s:
        return None
    m = re.search(r'\b(1[89]\d\d|20\d\d)\b', s)
    return int(m.group(1)) if m else None

def detect_timeline_gaps(profile: PersonProfile) -> list[tuple[int, int]]:
    """Find gaps in the timeline with adaptive thresholds based on age."""
    years = []
    
    # 1. Parse birth_date from profile
    birth_year = None
    if profile.birth_date:
        birth_year = _extract_first_year(profile.birth_date)
        if birth_year:
            years.append(birth_year)
            
    # 2. Parse claims
    timeline_fields = {"birth_date", "education", "affiliation", "position", "award", "death_date"}
    for claim in profile.claims:
        if claim.field not in timeline_fields:
            continue
        cy = _extract_first_year(claim.date_context) or _extract_first_year(claim.text)
        if cy:
            years.append(cy)
            
    if not years:
        return []
        
    years = sorted(list(set(years)))
    gaps = []
    
    # Check gaps between consecutive events
    last_year = years[0]
    for y in years[1:]:
        # Adaptive threshold:
        # If we know birth year, check if the period is early life (<= birth_year + 22)
        if birth_year and y <= birth_year + 22:
            threshold = 18  # Allow larger gap for childhood/early education
        else:
            threshold = 3   # 3 years during active career
            
        if y - last_year > threshold:
            gaps.append((last_year, y))
        last_year = max(last_year, y)
        
    # Check gap to present year if no death date
    has_death_date = any(c.field == "death_date" for c in profile.claims)
    present_year = datetime.now().year
    if not has_death_date:
        # Adaptive threshold for recent gap
        if birth_year and present_year <= birth_year + 22:
            threshold = 18
        else:
            threshold = 3
            
        if present_year - last_year > threshold:
            gaps.append((last_year, present_year))
            
    return gaps

# ── LLM query generation ───────────────────────────────────────────────────────
_SYSTEM = """\
You are a research assistant building a Wikipedia article.
Generate 6 targeted web search queries to find NEW sources about this SPECIFIC person.
CRITICAL: Every query must include the person's affiliation and/or field to avoid finding wrong people with the same name.
Avoid re-searching domains already consulted.
If there are timeline gaps listed, please generate at least 2 queries targeting those specific years or periods (e.g. including years in the query or ranges).
Return JSON only: {"queries": [{"query": "...", "seeking": "slot_name", "reason": "one line why"}]}"""


def _normalize_url(url: str) -> str:
    url = url.strip().lower()
    if url.startswith("https://"):
        url = url[8:]
    elif url.startswith("http://"):
        url = url[7:]
    if url.startswith("www."):
        url = url[4:]
    if "#" in url:
        url = url.split("#", 1)[0]
    if "?" in url:
        url = url.split("?", 1)[0]
    if url.endswith("/"):
        url = url[:-1]
    return url


def _generate_multiyear_report_urls(url: str) -> list[str]:
    import re
    host = urlparse(url).netloc.lower().replace("www.", "")
    _NO_SWEEP_HOSTS = (
        "doi.org", "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov",
        "nature.com", "springer.com", "link.springer.com", "wiley.com",
        "onlinelibrary.wiley.com", "plos.org", "journals.plos.org",
        "sciencedirect.com", "semanticscholar.org", "academic.oup.com",
        "tandfonline.com", "mdpi.com", "frontiersin.org", "researchgate.net",
    )
    if any(host == d or host.endswith("." + d) for d in _NO_SWEEP_HOSTS):
        return []
    m = re.search(r'\b(19\d\d|20[0-2]\d)\b', url)
    if not m:
        return []
    year = int(m.group(1))
    results = []
    for y in range(2000, 2026):
        if y != year:
            new_url = url[:m.start(1)] + str(y) + url[m.end(1):]
            results.append(new_url)
    return results


def _profile_link_suggestions(profile: PersonProfile, missing: list[str], seen_normalized: set[str]) -> list[dict]:
    """Pass 1 — warm leads: profile-shaped links already found on fetched pages."""
    suggestions = []
    for src in profile.sources:
        for link_url in src.profile_links:
            if _normalize_url(link_url) in seen_normalized:
                continue
            expected = ["affiliation", "education", "field", "known_for"]
            suggestions.append({
                "url": link_url,
                "title": link_url,
                "snippet": f"Found on: {src.title or src.url}",
                "reason": f"Profile link found on {src.publisher or src.title}",
                "expected_slots": expected,
                "priority": 0,
                "source_type": "profile",
                "fetchable": _fetchability(link_url),
                "relevance": "high",  # trusted — came from a verified page
                "completion_value": _completion_value(expected, missing),
            })
            seen_normalized.add(_normalize_url(link_url))
    return suggestions


def _multiyear_report_suggestions(profile: PersonProfile, missing: list[str], seen_normalized: set[str], budget: int) -> list[dict]:
    """Pass 1.5 — unverified institutional report guesses, bounded so real
    search results always keep queue slots."""
    suggestions = []
    for src in profile.sources:
        if len(suggestions) >= budget:
            break
        for report_url in _generate_multiyear_report_urls(src.url):
            if len(suggestions) >= budget:
                break
            if _normalize_url(report_url) in seen_normalized:
                continue
            expected = ["position", "award", "known_for"]
            suggestions.append({
                "url": report_url,
                "title": report_url,
                "snippet": f"Multi-year report series derived from {src.publisher or src.url}",
                "reason": f"Sequential institutional report derived from {src.publisher or 'source'}",
                "expected_slots": expected,
                "priority": 1,
                "source_type": "profile",
                "fetchable": _fetchability(report_url),
                "relevance": "high",
                "completion_value": _completion_value(expected, missing),
            })
            seen_normalized.add(_normalize_url(report_url))
    return suggestions


def _build_search_prompt(profile: PersonProfile, field: str, affil: str, missing: list[str], gaps: list[tuple[int, int]], sources_text: str) -> str:
    claims_text = "\n".join(f"- {c.field}: {c.text}" for c in profile.claims[:20]) or "None yet"
    missing_text = ", ".join(missing) or "none"
    gaps_text = ", ".join(f"{start}–{end} ({end - start} years)" for start, end in gaps) if gaps else "None detected"
    return f"""Person: {profile.name}
Field: {field}
Affiliation: {affil}

Known facts:
{claims_text}

Missing: {missing_text}

Timeline Gaps (periods with no sourced events):
{gaps_text}

Already consulted (avoid same domains unless a clearly different page):
{sources_text}

Every query MUST include "{affil}" or "{field}" as disambiguation.
If there are timeline gaps listed, please generate at least 2 queries targeting those specific years or periods (e.g. including years in the query or ranges)."""


def _search_queries(profile: PersonProfile, field: str, affil: str, missing: list[str], gaps: list[tuple[int, int]]) -> list[dict]:
    """LLM-generated queries, fallback templates, and site-restricted outlet queries."""
    from .llm import get_provider
    from .researcher import _NEWS_OUTLETS

    sources_text = "\n".join(f"- {s.url}" for s in profile.sources[:15]) or "None yet"
    queries: list[dict] = []
    try:
        raw = get_provider().complete(_SYSTEM, _build_search_prompt(profile, field, affil, missing, gaps, sources_text))
        queries = json.loads(raw).get("queries", [])
    except Exception:
        pass

    if not queries:
        fallback: dict[str, str] = {
            "birth_date":  f'"{profile.name}" {affil} biography born',
            "award":       f'"{profile.name}" {affil} award prize',
            "education":   f'"{profile.name}" {affil} PhD education',
            "known_for":   f'"{profile.name}" {affil} {field} contribution',
            "affiliation": f'"{profile.name}" {affil} faculty profile',
            "position":    f'"{profile.name}" {affil} {field} position',
        }
        for slot in missing[:6]:
            q = fallback.get(slot, f'"{profile.name}" {affil} {slot}')
            queries.append({"query": q.strip(), "seeking": slot, "reason": f"Likely has: {slot.replace('_', ' ')}"})
        for start, end in gaps[:2]:
            queries.append({
                "query": f'"{profile.name}" {affil} {start} {end}'.strip(),
                "seeking": "position",
                "reason": f"Search for career history during timeline gap {start}–{end}",
            })

    site_target = next((slot for slot in ("known_for", "award", "position") if slot in missing), "known_for")
    for outlet in _NEWS_OUTLETS:
        queries.append({
            "query": f'"{profile.name}" {affil or field} site:{outlet}'.strip(),
            "seeking": site_target,
            "reason": f"National outlet {outlet} coverage",
        })
    return queries


def _run_search_queries(queries: list[dict], profile: PersonProfile, affil: str, field: str, missing: list[str], seen_normalized: set[str], max_results: int) -> list[dict]:
    from .researcher import _search_web
    suggestions: list[dict] = []
    for item in queries:
        if len(suggestions) >= max_results:
            break
        query = item.get("query", "")
        seeking = item.get("seeking", "")
        reason = item.get("reason", f"Might have: {seeking.replace('_', ' ')}")
        if not query:
            continue
        results = _search_web(query)
        for r in results[:6]:
            if _normalize_url(r.url) in seen_normalized:
                continue
            rel = _relevance(r.title, r.snippet, affil, field, profile.claims)
            if rel == "low":
                continue  # skip wrong-person results
            expected = [seeking] if seeking else []
            if "birth_date" in expected:
                text_lower = (r.title + " " + r.snippet).lower()
                animal_kws = ["cloned", "cloning", "animal", "buffalo", "calf", "cow", "bull", "sheep", "goat", "offspring", "garima", "samrupa", "ganga", "dolly"]
                if any(akw in text_lower for akw in animal_kws):
                    expected = ["known_for"]
                    reason = "Likely has: cloning contribution"
            is_prof = is_profile_url(r.url)
            prio = 0 if "site:" in query else (1 if is_prof else 2)
            stype = "profile" if is_prof else _classify_source_type(r.url, r.title)
            suggestions.append({
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "reason": reason,
                "query": query,
                "expected_slots": expected,
                "priority": prio,
                "source_type": stype,
                "fetchable": _fetchability(r.url),
                "relevance": rel,
                "completion_value": _completion_value(expected, missing),
            })
            seen_normalized.add(_normalize_url(r.url))
            break
    return suggestions


def suggest_next_urls(profile: PersonProfile, max_results: int = 8) -> list[dict]:
    """Return ranked URL suggestions — profile links & multi-year reports first, then web searches."""

    existing_urls = {s.url for s in profile.sources}
    skipped_urls = set(getattr(profile, "skipped_sources", []) or [])
    rejected_urls = set(getattr(profile, "rejected_sources", []) or [])
    seen_normalized = {_normalize_url(u) for u in (existing_urls | skipped_urls | rejected_urls)}
    affil = profile.affiliation or ""
    field = profile.field or ""
    missing = profile.missing_slots

    suggestions = _profile_link_suggestions(profile, missing, seen_normalized)
    suggestions += _multiyear_report_suggestions(profile, missing, seen_normalized, max(max_results - 2, 0))

    if len(suggestions) < max_results:
        gaps = detect_timeline_gaps(profile)
        queries = _search_queries(profile, field, affil, missing, gaps)
        suggestions += _run_search_queries(queries, profile, affil, field, missing, seen_normalized, max_results)

    # Sort: profile links first, then by completion_value × relevance weight
    _rel_weight = {"high": 3, "medium": 2, "low": 1}
    suggestions.sort(key=lambda s: (
        s["priority"],
        -s["completion_value"] * _rel_weight.get(s.get("relevance", "medium"), 2),
    ))
    return suggestions[:max_results]
