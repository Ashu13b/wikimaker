"""Extract profile-shaped outbound links from a fetched page."""
from __future__ import annotations
from urllib.parse import urljoin, urlparse

# Domains that strongly indicate a researcher/person profile
_PROFILE_DOMAINS = {
    "scholar.google.com", "scholar.google.co.in",
    "orcid.org",
    "researchgate.net",
    "scopus.com",
    "linkedin.com",
    "semanticscholar.org",
    "webofscience.com",
    "loop.frontiersin.org",
    "openalex.org",
    "publons.com",
    "academia.edu",
}

# Path fragments that indicate a profile page on institutional sites
_PROFILE_PATH_FRAGMENTS = [
    "/faculty/", "/staff/", "/people/", "/profile/", "/researcher/",
    "/person/", "/member/", "/author/", "/scientist/", "/academic/",
    "/en/persons/", "/en/researchers/", "/scientists/", "/experts/",
    "/our-team/", "/team/",
]


def extract_profile_links(raw_html: str, person_name: str, base_url: str) -> list[str]:
    """Return URLs from raw_html that look like profile pages for this person."""
    if not raw_html:
        return []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_html, "html.parser")
    except Exception:
        return []

    name_lower = person_name.lower()
    name_parts = [p.lower() for p in person_name.split() if len(p) > 2]

    found: list[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        domain = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.lower()
        anchor = a.get_text(" ", strip=True).lower()

        is_profile = False

        # Known profile domains
        for pd in _PROFILE_DOMAINS:
            if domain == pd or domain.endswith("." + pd):
                is_profile = True
                break

        # Profile path pattern on any domain
        if not is_profile:
            for frag in _PROFILE_PATH_FRAGMENTS:
                if frag in path:
                    is_profile = True
                    break

        # Anchor text contains the person's name
        if not is_profile:
            if name_lower in anchor or (len(name_parts) >= 2 and all(p in anchor for p in name_parts[:2])):
                is_profile = True

        if is_profile and url not in seen:
            seen.add(url)
            found.append(url)

    return found[:20]
