"""Goal-directed URL suggestion engine.

Suggestion queue is fed from two sources:
1. Profile links extracted from already-fetched pages (high priority — warm leads)
2. LLM-generated web searches anchored to affiliation + field (fallback)

Each suggestion carries: fetchable, relevance, completion_value.
"""
from __future__ import annotations
import json
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


# ── LLM query generation ───────────────────────────────────────────────────────
_SYSTEM = """\
You are a research assistant building a Wikipedia article.
Generate 6 targeted web search queries to find NEW sources about this SPECIFIC person.
CRITICAL: Every query must include the person's affiliation and/or field to avoid finding wrong people with the same name.
Avoid re-searching domains already consulted.
Return JSON only: {"queries": [{"query": "...", "seeking": "slot_name", "reason": "one line why"}]}"""


def suggest_next_urls(profile: PersonProfile, max_results: int = 8) -> list[dict]:
    """Return ranked URL suggestions — profile links first, then web searches."""
    from .researcher import _search_web
    from .llm import get_provider

    existing_urls = {s.url for s in profile.sources}
    seen_urls: set[str] = set(existing_urls)
    affil = profile.affiliation or ""
    field = profile.field or ""
    missing = profile.missing_slots

    suggestions: list[dict] = []

    # ── Pass 1: profile links from already-fetched sources (warm leads) ────────
    for src in profile.sources:
        for link_url in src.profile_links:
            if link_url in seen_urls:
                continue
            expected = ["affiliation", "education", "field", "known_for"]
            suggestions.append({
                "url": link_url,
                "title": link_url,
                "snippet": f"Found on: {src.title or src.url}",
                "reason": f"Profile link found on {src.publisher or src.title}",
                "expected_slots": expected,
                "priority": 0,
                "fetchable": _fetchability(link_url),
                "relevance": "high",  # trusted — came from a verified page
                "completion_value": _completion_value(expected, missing),
            })
            seen_urls.add(link_url)

    # ── Pass 2: LLM-generated web searches ────────────────────────────────────
    if len(suggestions) < max_results:
        claims_text = "\n".join(f"- {c.field}: {c.text}" for c in profile.claims[:20]) or "None yet"
        sources_text = "\n".join(f"- {s.url}" for s in profile.sources[:15]) or "None yet"
        missing_text = ", ".join(missing) or "none"

        prompt = f"""Person: {profile.name}
Field: {field}
Affiliation: {affil}

Known facts:
{claims_text}

Missing: {missing_text}

Already consulted (avoid same domains unless a clearly different page):
{sources_text}

Every query MUST include "{affil}" or "{field}" as disambiguation."""

        queries = []
        try:
            raw = get_provider().complete(_SYSTEM, prompt)
            queries = json.loads(raw).get("queries", [])
        except Exception:
            pass

        if not queries:
            _FALLBACK: dict[str, str] = {
                "birth_date":  f'"{profile.name}" {affil} biography born',
                "award":       f'"{profile.name}" {affil} award prize',
                "education":   f'"{profile.name}" {affil} PhD education',
                "known_for":   f'"{profile.name}" {affil} {field} contribution',
                "affiliation": f'"{profile.name}" {affil} faculty profile',
                "position":    f'"{profile.name}" {affil} {field} position',
            }
            for slot in missing[:6]:
                q = _FALLBACK.get(slot, f'"{profile.name}" {affil} {slot}')
                queries.append({"query": q.strip(), "seeking": slot, "reason": f"Likely has: {slot.replace('_', ' ')}"})

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
                if r.url in seen_urls:
                    continue
                rel = _relevance(r.title, r.snippet, affil, field, profile.claims)
                if rel == "low":
                    continue  # skip wrong-person results
                expected = [seeking] if seeking else []
                suggestions.append({
                    "url": r.url,
                    "title": r.title,
                    "snippet": r.snippet,
                    "reason": reason,
                    "query": query,
                    "expected_slots": expected,
                    "priority": 1,
                    "fetchable": _fetchability(r.url),
                    "relevance": rel,
                    "completion_value": _completion_value(expected, missing),
                })
                seen_urls.add(r.url)
                break

    # Sort: profile links first, then by completion_value × relevance weight
    _rel_weight = {"high": 3, "medium": 2, "low": 1}
    suggestions.sort(key=lambda s: (
        s["priority"],
        -s["completion_value"] * _rel_weight.get(s.get("relevance", "medium"), 2),
    ))
    return suggestions[:max_results]
