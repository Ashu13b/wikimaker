"""Gather sources for a person: Semantic Scholar + Google CSE + DuckDuckGo + user-provided URLs."""
from __future__ import annotations
import os
import requests
from bs4 import BeautifulSoup
from .models import Source, SourceReliability

HEADERS = {"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)"}
S2_API = "https://api.semanticscholar.org/graph/v1"
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


def fetch_auto_sources(
    name: str,
    field: str | None = None,
    affiliation: str | None = None,
) -> tuple[list[Source], str | None]:
    """Returns (sources, s2_author_id). s2_author_id is None if no S2 match found."""
    sources: list[Source] = []
    s2_sources, s2_author_id = _semantic_scholar(name, affiliation)
    sources.extend(s2_sources)
    # Academic-context search (field + affiliation)
    sources.extend(_google_cse(name, field, affiliation))
    sources.extend(_duckduckgo_html(name, field, affiliation))
    # News/biography search — name + one disambiguator to avoid wrong-person results
    disambig = (affiliation or "").split()[0] if affiliation else (field or "").split()[0] if field else ""
    bio_query = f'"{name}" {disambig}'.strip()
    bio_sources = _search_web(bio_query)
    seen = {s.url for s in sources}
    sources.extend(s for s in bio_sources if s.url not in seen)
    return sources, s2_author_id


def fetch_url_source(url: str, person_name: str = "") -> tuple[Source, bool]:
    """Fetch a user-provided URL. Returns (Source, blocked).
    If blocked=True, caller should ask user to paste text or upload screenshot."""
    from .fetcher import fetch_url
    from .link_extractor import extract_profile_links
    result = fetch_url(url)

    if result.blocked:
        return Source(
            url=url, title=url, publisher=_extract_publisher(url),
            reliability=SourceReliability.primary,
            snippet="", user_provided=True,
        ), True

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(result.text[:10000], "html.parser") if "<html" in result.text[:200] else None
        title = soup.title.string.strip() if (soup and soup.title) else url
    except Exception:
        title = url

    profile_links = extract_profile_links(result.raw_html, person_name, url) if person_name else []

    return Source(
        url=url, title=title, publisher=_extract_publisher(url),
        reliability=SourceReliability.primary,  # classifier will re-tag
        snippet=result.text[:400], user_provided=True,
        profile_links=profile_links,
    ), False


def fetch_url_source_with_paste(url: str, pasted_text: str) -> Source:
    """Build a Source from user-pasted text for a blocked URL."""
    from .fetcher import fetch_text_paste
    result = fetch_text_paste(url, pasted_text)
    return Source(
        url=url, title=_extract_publisher(url), publisher=_extract_publisher(url),
        reliability=SourceReliability.primary,
        snippet=pasted_text[:400], user_provided=True,
    )


def _semantic_scholar(name: str, affiliation: str | None = None) -> tuple[list[Source], str | None]:
    """Returns (sources, author_id)."""
    try:
        resp = requests.get(f"{S2_API}/author/search",
            params={"query": name, "fields": "name,affiliations,paperCount,citationCount", "limit": 5},
            timeout=10)
        resp.raise_for_status()
        candidates = resp.json().get("data", [])
    except Exception:
        return [], None

    if not candidates:
        return [], None

    author_id = _pick_author_id(candidates, name, affiliation or "")
    if not author_id:
        return [], None

    try:
        papers_resp = requests.get(f"{S2_API}/author/{author_id}/papers",
            params={"fields": "title,year,externalIds,citationCount,venue", "limit": 8},
            timeout=10)
        papers_resp.raise_for_status()
        papers = papers_resp.json().get("data", [])
    except Exception:
        return [], author_id

    sources = []
    for paper in papers:
        doi = paper.get("externalIds", {}).get("DOI")
        url = f"https://doi.org/{doi}" if doi else f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}"
        sources.append(Source(
            url=url,
            title=paper.get("title", ""),
            publisher=paper.get("venue") or "Academic publication",
            reliability=SourceReliability.reliable_secondary,
            snippet=f"Published {paper.get('year', 'unknown year')}, cited {paper.get('citationCount', 0)} times.",
            date=str(paper.get("year")) if paper.get("year") else None,
            fetched_by="semantic_scholar",
        ))
    return sources, author_id


def _pick_author_id(candidates: list[dict], name: str, affiliation: str) -> str | None:
    """Pick the S2 authorId that most likely matches this person.

    Strategy: validate each candidate by checking one of their DOI papers
    against CrossRef. The first candidate whose paper confirms the person's
    name is the right one. Falls back to highest paper-count candidate if
    CrossRef can't resolve any.
    """
    from .author_check import check_doi_authors, name_variants

    affil_kw = [w.lower() for w in affiliation.split() if len(w) > 3]

    # Score candidates: affiliation keyword match in S2 affiliation data
    def affil_score(candidate: dict) -> int:
        text = " ".join(a.get("name", "") for a in candidate.get("affiliations", [])).lower()
        return sum(1 for kw in affil_kw if kw in text)

    # Sort: affiliation matches first, then by paper count (more = more likely right person)
    ranked = sorted(candidates, key=lambda c: (affil_score(c), c.get("paperCount", 0)), reverse=True)

    for candidate in ranked:
        cid = candidate.get("authorId")
        if not cid:
            continue
        # Quick validation: fetch a few papers and CrossRef-check the first DOI
        try:
            pr = requests.get(f"{S2_API}/author/{cid}/papers",
                params={"fields": "externalIds", "limit": 5}, timeout=8)
            pr.raise_for_status()
            papers = pr.json().get("data", [])
        except Exception:
            continue

        for paper in papers:
            doi = paper.get("externalIds", {}).get("DOI")
            if not doi:
                continue
            result = check_doi_authors(doi, name, affiliation)
            if result["status"] in ("confirmed", "possible"):
                return cid
            if result["status"] in ("wrong_person", "not_found"):
                break  # this candidate is wrong, try the next one

    # No CrossRef validation succeeded — fall back to highest paper count
    return ranked[0].get("authorId") if ranked else None


def _google_cse(name: str, field: str | None, affiliation: str | None) -> list[Source]:
    key = os.environ.get("GOOGLE_CSE_KEY")
    cx = os.environ.get("GOOGLE_CSE_CX")
    if not key or not cx:
        return []

    query = " ".join(filter(None, [f'"{name}"', field, affiliation]))
    try:
        resp = requests.get(GOOGLE_CSE_URL, params={
            "key": key, "cx": cx, "q": query, "num": 10,
        }, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception:
        return []

    sources = []
    for item in items:
        url = item.get("link", "")
        if not url:
            continue
        sources.append(Source(
            url=url,
            title=item.get("title", url),
            publisher=_extract_publisher(url),
            reliability=SourceReliability.primary,  # classifier will re-tag
            snippet=item.get("snippet", "")[:400],
            fetched_by="google_search",
        ))
    return sources


def _duckduckgo_html(name: str, field: str | None, affiliation: str | None) -> list[Source]:
    """DuckDuckGo web search via ddgs library — fallback when Google CSE is not configured."""
    if os.environ.get("GOOGLE_CSE_KEY"):
        return []  # skip if Google is available

    query = " ".join(filter(None, [f'"{name}"', field, affiliation]))
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=10))
    except Exception:
        return []

    sources = []
    for r in results:
        url = r.get("href", "")
        title = r.get("title", "")
        snippet = r.get("body", "")
        if url and title:
            sources.append(Source(
                url=url,
                title=title,
                publisher=_extract_publisher(url),
                reliability=SourceReliability.primary,
                snippet=snippet[:400],
                fetched_by="duckduckgo",
            ))
    return sources


def _extract_publisher(url: str) -> str:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        return host.replace("www.", "")
    except Exception:
        return url


# ── Targeted slot search ───────────────────────────────────────────────────────

_SLOT_QUERIES: dict[str, str] = {
    "birth_date":  '"{name}" born',
    "birth_place": '"{name}" born place',
    "education":   '"{name}" education degree PhD',
    "position":    '"{name}" scientist professor director',
    "award":       '"{name}" award prize fellow',
    "known_for":   '"{name}" research work contributions',
    "nationality": '"{name}" biography',
    "full_name":   '"{name}" profile bio',
    "affiliation": '"{name}" department institute',
}


def _search_web(query: str) -> list[Source]:
    """Run an arbitrary query through Google CSE or DDG."""
    key = os.environ.get("GOOGLE_CSE_KEY")
    cx = os.environ.get("GOOGLE_CSE_CX")
    if key and cx:
        try:
            resp = requests.get(GOOGLE_CSE_URL, params={"key": key, "cx": cx, "q": query, "num": 8}, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [Source(
                url=item["link"], title=item.get("title", item["link"]),
                publisher=_extract_publisher(item["link"]),
                reliability=SourceReliability.primary,
                snippet=item.get("snippet", "")[:400],
                fetched_by="google_search",
            ) for item in items if item.get("link")]
        except Exception:
            pass

    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))
        return [Source(
            url=r["href"], title=r.get("title", r["href"]),
            publisher=_extract_publisher(r["href"]),
            reliability=SourceReliability.primary,
            snippet=r.get("body", "")[:400],
            fetched_by="duckduckgo",
        ) for r in results if r.get("href")]
    except Exception:
        return []


def targeted_slot_search(
    person_name: str,
    slot: str,
    field: str | None = None,
    affiliation: str | None = None,
    hint: str | None = None,
) -> list[Source]:
    """Search web for sources likely to contain a specific Wikipedia slot value."""
    template = _SLOT_QUERIES.get(slot, '"{name}"')
    query = template.format(name=person_name)
    if hint:
        query += f" {hint}"
    elif affiliation and slot in ("education", "position", "affiliation", "known_for"):
        query += f" {affiliation}"
    elif field and slot in ("known_for", "position"):
        query += f" {field}"
    return _search_web(query)


# ── Institution crawl ──────────────────────────────────────────────────────────

def _find_institution_url(affiliation: str) -> str | None:
    """Search for the official website of an institution."""
    sources = _search_web(f"{affiliation} official website")
    institutional_tlds = (".edu", ".ac.", ".res.in", ".gov", ".edu.in", ".ac.in", ".org")
    for s in sources:
        if any(tld in s.url for tld in institutional_tlds):
            from urllib.parse import urlparse
            p = urlparse(s.url)
            return f"{p.scheme}://{p.netloc}"
    # Fallback: first result's base URL
    if sources:
        from urllib.parse import urlparse
        p = urlparse(sources[0].url)
        return f"{p.scheme}://{p.netloc}"
    return None


def fetch_institution_sources(person_name: str, affiliation: str) -> list[Source]:
    """Crawl the institution's website to find the person's staff/faculty page."""
    institution_url = _find_institution_url(affiliation)
    if not institution_url:
        return []

    from .crawler import crawl
    graph = crawl(
        seed_urls=[institution_url],
        person_name=person_name,
        keywords=[affiliation, "scientist", "staff", "faculty"],
        max_nodes=25,
        max_depth=2,
    )
    relevant = [
        s for s in graph.to_sources(None)
        if graph.relevance_hits.get(s.url, 0) > 0
    ]
    for s in relevant:
        s.fetched_by = "crawl"
    return relevant
