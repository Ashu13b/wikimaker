"""Phase 1: find candidate cards for a person name + hints."""
from __future__ import annotations
import re
import requests
from .models import PersonCandidate

HEADERS = {"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)"}
WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"


def fetch_wikidata_photo(name: str) -> str | None:
    """Try Wikidata for a photo. Only uses results whose name tokens exactly match."""
    try:
        resp = requests.get(WIKIDATA_API, params={
            "action": "wbsearchentities", "search": name,
            "language": "en", "type": "item", "limit": "3", "format": "json",
        }, headers=HEADERS, timeout=8)
        resp.raise_for_status()
    except Exception:
        return None

    searched_tokens = set(_significant_tokens(name))
    for r in resp.json().get("search", []):
        label = r.get("label", "")
        if set(_significant_tokens(label)) != searched_tokens:
            continue
        if not _looks_like_person(r.get("description", "")):
            continue
        detail = _wikidata_detail(r["id"])
        if detail.get("photo_url"):
            return detail["photo_url"]
    return None


def find_candidates(name: str, hints: str = "") -> list[PersonCandidate]:
    wiki = _search_wikipedia(name, hints)
    wdata = _search_wikidata(name, hints)

    seen_ids = {c.wikidata_id for c in wiki if c.wikidata_id}
    merged = list(wiki)
    for c in wdata:
        if c.wikidata_id not in seen_ids:
            merged.append(c)
            seen_ids.add(c.wikidata_id)
    return merged[:5]


_HONORIFICS = {"dr", "dr.", "prof", "prof.", "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "sir", "shri"}


def _significant_tokens(name: str) -> list[str]:
    """Strip honorifics and parenthetical disambiguators; return meaningful name tokens."""
    tokens = []
    for t in name.lower().split():
        t = t.strip("()")
        if t and t not in _HONORIFICS:
            tokens.append(t)
    return tokens


def _name_matches(candidate_title: str, searched_name: str) -> bool:
    """Every significant token of the searched name must appear in the candidate title.
    'Prem Kumar' does not match 'Prem Singh Yadav' because 'singh'/'yadav' are absent."""
    searched_tokens = _significant_tokens(searched_name)
    candidate_tokens = set(_significant_tokens(candidate_title))
    return all(t in candidate_tokens for t in searched_tokens)


def _search_wikipedia(name: str, hints: str) -> list[PersonCandidate]:
    # Search with just the name so Wikipedia doesn't boost unrelated articles via hints
    try:
        resp = requests.get(WIKI_API, params={
            "action": "query", "list": "search",
            "srsearch": name, "srnamespace": "0",
            "srlimit": "10", "format": "json",
        }, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    hint_words = [w.lower() for w in hints.split() if len(w) > 2] if hints else []

    results = resp.json().get("query", {}).get("search", [])
    candidates = []
    for r in results:
        title = r["title"]
        if not _name_matches(title, name):
            continue
        snippet = _strip_html(r.get("snippet", ""))
        if hint_words:
            hint_score = sum(1 for w in hint_words if w in snippet.lower() or w in title.lower())
            # When hints are given, drop candidates that match none of them
            if hint_score == 0:
                continue
        else:
            hint_score = 0
        detail = _wikipedia_detail(title)
        candidates.append((hint_score, PersonCandidate(
            name=title,
            photo_url=detail.get("photo_url"),
            bio_snippet=snippet,
            wikipedia_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
            wikidata_id=detail.get("wikidata_id"),
        )))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in candidates[:5]]


def _search_wikidata(name: str, hints: str = "") -> list[PersonCandidate]:
    hint_words = [w.lower() for w in hints.split() if len(w) > 2] if hints else []

    try:
        resp = requests.get(WIKIDATA_API, params={
            "action": "wbsearchentities", "search": name,
            "language": "en", "type": "item", "limit": "5", "format": "json",
        }, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    candidates = []
    for r in resp.json().get("search", []):
        desc = r.get("description", "")
        label = r.get("label", "")
        if not _looks_like_person(desc):
            continue
        if not _name_matches(label, name):
            continue
        if hint_words:
            hint_score = sum(1 for w in hint_words if w in desc.lower() or w in label.lower())
            if hint_score == 0:
                continue
        detail = _wikidata_detail(r["id"])
        candidates.append(PersonCandidate(
            name=r.get("label", name),
            photo_url=detail.get("photo_url"),
            bio_snippet=desc,
            birth_year=detail.get("birth_year"),
            nationality=detail.get("nationality"),
            field=detail.get("field"),
            affiliation=detail.get("affiliation"),
            wikipedia_url=detail.get("wikipedia_url"),
            wikidata_id=r["id"],
        ))
    return candidates


def _wikipedia_detail(title: str) -> dict:
    try:
        resp = requests.get(WIKI_API, params={
            "action": "query", "titles": title,
            "prop": "pageimages|pageprops",
            "pithumbsize": "300", "format": "json",
        }, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception:
        return {}
    pages = resp.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    return {
        "photo_url": page.get("thumbnail", {}).get("source"),
        "wikidata_id": page.get("pageprops", {}).get("wikibase_item"),
    }


def _wikidata_detail(qid: str) -> dict:
    try:
        resp = requests.get(WIKIDATA_API, params={
            "action": "wbgetentities", "ids": qid,
            "props": "claims|sitelinks", "format": "json",
        }, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception:
        return {}

    entity = resp.json().get("entities", {}).get(qid, {})
    claims = entity.get("claims", {})

    def _val(prop: str) -> str | None:
        items = claims.get(prop, [])
        if not items:
            return None
        dv = items[0].get("mainsnak", {}).get("datavalue", {})
        if dv.get("type") == "time":
            return dv["value"]["time"][1:5]  # year only
        if dv.get("type") == "string":
            return dv["value"]
        return None

    enwiki = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
    return {
        "birth_year": _val("P569"),
        "nationality": _val("P27"),
        "field": _val("P101"),
        "affiliation": _val("P108"),
        "photo_url": _wikidata_image(claims),
        "wikipedia_url": f"https://en.wikipedia.org/wiki/{enwiki.replace(' ', '_')}" if enwiki else None,
    }


def _wikidata_image(claims: dict) -> str | None:
    items = claims.get("P18", [])
    if not items:
        return None
    filename = items[0].get("mainsnak", {}).get("datavalue", {}).get("value", "")
    if not filename:
        return None
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename.replace(' ', '_')}?width=300"


def _looks_like_person(description: str) -> bool:
    keywords = {
        "researcher", "scientist", "professor", "academic", "politician",
        "author", "writer", "physician", "doctor", "engineer", "activist",
        "journalist", "economist", "philosopher", "historian", "artist", "born",
    }
    return any(kw in description.lower() for kw in keywords)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
