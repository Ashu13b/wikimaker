"""Find and validate researcher profile IDs: ORCID, Google Scholar, Semantic Scholar, Scopus."""
from __future__ import annotations
import re
import requests
from .models import Source, SourceReliability

HEADERS = {"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)", "Accept": "application/json"}
OA_HEADERS = {"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)", "Accept": "application/json"}

# URL patterns to extract IDs from
_ORCID_RE = re.compile(r"orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])")
_SCHOLAR_RE = re.compile(r"scholar\.google\.com/citations\?.*?user=([A-Za-z0-9_-]+)")
_SCOPUS_RE = re.compile(r"scopus\.com/authid/detail\.uri\?authorId=(\d+)")
# ScienceDirect author profile: /author/<scopus_id>/<name>
_SD_AUTHOR_RE = re.compile(r"sciencedirect\.com/author/(\d+)/")
_RESEARCHGATE_RE = re.compile(r"researchgate\.net/profile/([A-Za-z0-9_-]+)")
_S2_AUTHOR_RE = re.compile(r"semanticscholar\.org/author/[^/]+/(\d+)")
# ScienceDirect article PII (Publisher Item Identifier)
_SD_PII_RE = re.compile(r"sciencedirect\.com/science/article/(?:abs/)?pii/([A-Z0-9]+)", re.I)


def extract_ids_from_sources(sources: list[Source]) -> dict[str, str]:
    """Pull researcher profile IDs directly from URLs in existing sources."""
    ids: dict[str, str] = {}
    for s in sources:
        url = s.url
        if not ids.get("orcid") and (m := _ORCID_RE.search(url)):
            ids["orcid"] = m.group(1)
        if not ids.get("google_scholar") and (m := _SCHOLAR_RE.search(url)):
            ids["google_scholar"] = m.group(1)
        if not ids.get("scopus") and (m := _SCOPUS_RE.search(url)):
            ids["scopus"] = m.group(1)
        if not ids.get("scopus") and (m := _SD_AUTHOR_RE.search(url)):
            ids["scopus"] = m.group(1)
        if not ids.get("researchgate") and (m := _RESEARCHGATE_RE.search(url)):
            ids["researchgate"] = m.group(1)
        if not ids.get("semantic_scholar") and (m := _S2_AUTHOR_RE.search(url)):
            ids["semantic_scholar"] = m.group(1)
    return ids


def search_researcher_ids(
    name: str,
    field: str | None = None,
    affiliation: str | None = None,
) -> dict[str, str]:
    """Actively search for researcher profile IDs via web search."""
    from .researcher import _search_web

    ids: dict[str, str] = {}
    context = affiliation or field or ""

    # ORCID search
    if not ids.get("orcid"):
        orcid_hits = _search_web(f'"{name}" site:orcid.org')
        for s in orcid_hits:
            if m := _ORCID_RE.search(s.url):
                ids["orcid"] = m.group(1)
                break

    # Google Scholar search
    if not ids.get("google_scholar"):
        gs_hits = _search_web(f'"{name}" {context} site:scholar.google.com'.strip())
        for s in gs_hits:
            if m := _SCHOLAR_RE.search(s.url):
                ids["google_scholar"] = m.group(1)
                break

    # Scopus search
    if not ids.get("scopus"):
        sc_hits = _search_web(f'"{name}" site:scopus.com/authid')
        for s in sc_hits:
            if m := _SCOPUS_RE.search(s.url):
                ids["scopus"] = m.group(1)
                break

    # ResearchGate search (lower priority, often unreliable identity)
    if not ids.get("researchgate"):
        rg_hits = _search_web(f'"{name}" {context} site:researchgate.net/profile'.strip())
        for s in rg_hits:
            if m := _RESEARCHGATE_RE.search(s.url):
                ids["researchgate"] = m.group(1)
                break

    return ids


def validate_orcid(orcid_id: str, name: str, affiliation: str | None = None) -> bool:
    """Call ORCID public API to cross-check name and affiliation."""
    try:
        resp = requests.get(
            f"https://pub.orcid.org/v3.0/{orcid_id}/record",
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code != 200:
            return False
        data = resp.json()

        # Check name match
        person = data.get("person", {})
        given = (person.get("name", {}).get("given-names", {}) or {}).get("value", "").lower()
        family = (person.get("name", {}).get("family-name", {}) or {}).get("value", "").lower()
        full = f"{given} {family}".strip()
        name_tokens = [t.lower() for t in name.split() if len(t) > 2]
        if not any(t in full for t in name_tokens):
            return False

        if affiliation:
            # Check employment/education affiliations
            affiliations_section = data.get("activities-summary", {}).get("employments", {})
            affil_groups = affiliations_section.get("affiliation-group", [])
            affil_text = " ".join(
                (g.get("summaries", [{}])[0].get("employment-summary", {})
                    .get("organization", {}).get("name", "")).lower()
                for g in affil_groups
            )
            affil_tokens = [t.lower() for t in affiliation.split() if len(t) > 3]
            if affil_tokens and not any(t in affil_text for t in affil_tokens):
                return False

        return True
    except Exception:
        return False


def fetch_orcid_works(orcid_id: str) -> list[Source]:
    """Fetch publication list from ORCID and return as Sources."""
    try:
        resp = requests.get(
            f"https://pub.orcid.org/v3.0/{orcid_id}/works",
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    sources: list[Source] = []
    for group in data.get("group", []):
        summaries = group.get("work-summary", [])
        if not summaries:
            continue
        summary = summaries[0]
        title = (summary.get("title", {}).get("title", {}) or {}).get("value", "")
        year = (summary.get("publication-date", {}) or {}).get("year", {})
        year_val = (year or {}).get("value") if isinstance(year, dict) else None
        journal = (summary.get("journal-title", {}) or {}).get("value", "")
        ext_ids = group.get("external-ids", {}).get("external-id", [])
        doi = next(
            (e["external-id-value"] for e in ext_ids if e.get("external-id-type") == "doi"),
            None,
        )
        url = f"https://doi.org/{doi}" if doi else f"https://orcid.org/{orcid_id}"
        if not title:
            continue
        sources.append(Source(
            url=url,
            title=title,
            publisher=journal or "Academic publication",
            reliability=SourceReliability.reliable_secondary,
            snippet=f"Published {year_val or 'unknown year'}.",
            date=str(year_val) if year_val else None,
            fetched_by="orcid",
        ))

    return sources


def extract_sd_pii(url: str) -> str | None:
    """Return the PII from a ScienceDirect article URL, or None."""
    m = _SD_PII_RE.search(url)
    return m.group(1) if m else None


def is_sd_article_url(url: str) -> bool:
    return bool(_SD_PII_RE.search(url))


def is_sd_author_url(url: str) -> bool:
    return bool(_SD_AUTHOR_RE.search(url))


def resolve_sd_article(url: str) -> dict | None:
    """PII → CrossRef DOI → OpenAlex author IDs.

    Returns:
        {doi, title, year, publisher, crossref_authors: [{given, family}],
         openalex_authorships: [{name, openalex_id}]}
    or None if the PII can't be resolved.
    """
    pii = extract_sd_pii(url)
    if not pii:
        return None

    # Step 1: CrossRef by alternative-id (PII)
    try:
        cr = requests.get(
            "https://api.crossref.org/works",
            params={"filter": f"alternative-id:{pii}", "rows": 1},
            headers={"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)"},
            timeout=12,
        )
        cr.raise_for_status()
        items = cr.json().get("message", {}).get("items", [])
    except Exception:
        return None

    if not items:
        return None

    item = items[0]
    doi = item.get("DOI")
    if not doi:
        return None

    title_list = item.get("title", [])
    title = title_list[0] if title_list else ""
    year = (item.get("published", {}).get("date-parts", [[None]])[0] or [None])[0]
    publisher = item.get("publisher", "Elsevier BV")
    crossref_authors = item.get("author", [])

    # Step 2: OpenAlex by DOI → get OpenAlex author IDs
    openalex_authorships: list[dict] = []
    try:
        oa = requests.get(
            f"https://api.openalex.org/works/doi:{doi}",
            headers=OA_HEADERS,
            timeout=12,
        )
        if oa.status_code == 200:
            for authorship in oa.json().get("authorships", []):
                author = authorship.get("author", {})
                oa_id = (author.get("id") or "").split("/")[-1]  # strip URL prefix
                openalex_authorships.append({
                    "name": author.get("display_name", ""),
                    "openalex_id": oa_id or None,
                })
    except Exception:
        pass

    return {
        "doi": doi,
        "title": title,
        "year": year,
        "publisher": publisher,
        "crossref_authors": crossref_authors,
        "openalex_authorships": openalex_authorships,
    }


def find_openalex_id_for_person(
    person_name: str,
    openalex_authorships: list[dict],
) -> str | None:
    """Given the authorship list from a paper, find the OpenAlex author ID for person_name."""
    name_tokens = [t.lower() for t in person_name.split() if len(t) > 2]
    for auth in openalex_authorships:
        name = auth.get("name", "").lower()
        if all(t in name for t in name_tokens):
            return auth.get("openalex_id")
    return None


def fetch_openalex_works(openalex_author_id: str, limit: int = 30) -> list[Source]:
    """Fetch full publication list from OpenAlex for a confirmed author ID."""
    try:
        resp = requests.get(
            "https://api.openalex.org/works",
            params={
                "filter": f"author.id:{openalex_author_id}",
                "select": "title,doi,publication_year,primary_location",
                "per-page": limit,
            },
            headers=OA_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        works = resp.json().get("results", [])
    except Exception:
        return []

    sources: list[Source] = []
    for w in works:
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        url = f"https://doi.org/{doi}" if doi else ""
        if not url:
            continue
        loc = (w.get("primary_location") or {})
        journal = (loc.get("source") or {}).get("display_name") or "Academic publication"
        year = w.get("publication_year")
        sources.append(Source(
            url=url,
            title=w.get("title", ""),
            publisher=journal,
            reliability=SourceReliability.reliable_secondary,
            snippet=f"Published {year or 'unknown year'}.",
            date=str(year) if year else None,
            fetched_by="openalex",
        ))
    return sources


def fetch_s2_author_papers(author_id: str, limit: int = 20) -> list[Source]:
    """Fetch papers for a confirmed Semantic Scholar author ID."""
    S2_API = "https://api.semanticscholar.org/graph/v1"
    try:
        resp = requests.get(
            f"{S2_API}/author/{author_id}/papers",
            params={"fields": "title,year,externalIds,citationCount,venue", "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        papers = resp.json().get("data", [])
    except Exception:
        return []

    sources: list[Source] = []
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
    return sources
