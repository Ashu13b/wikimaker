"""Multi-strategy URL fetcher with fallbacks for blocked sources."""
from __future__ import annotations
import requests
from urllib.parse import quote_plus, urlparse

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
BOT_HEADERS = {"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)"}  # for APIs that want bot UA
TIMEOUT = 10


class FetchResult:
    def __init__(self, url: str, text: str, method: str, blocked: bool = False, raw_html: str = ""):
        self.url = url
        self.text = text          # extracted text content (paragraphs only)
        self.raw_html = raw_html  # full HTML — for link extraction in crawler
        self.method = method      # direct | wayback | orcid | blocked
        self.blocked = blocked    # True = needs user paste or screenshot


BROWSER_SERVER = "http://localhost:7070"


def _try_browser_server(url: str) -> FetchResult | None:
    """Fetch via the human browser_server if it's running. Returns None if unavailable."""
    try:
        st = requests.get(f"{BROWSER_SERVER}/status", timeout=1).json()
        if not st.get("running"):
            return None
        nav = requests.post(f"{BROWSER_SERVER}/navigate", json={"url": url}, timeout=30).json()
        if nav.get("error"):
            return None
        data = requests.get(f"{BROWSER_SERVER}/content", timeout=5).json()
        text = data.get("text", "").strip()
        # Treat short content as possible CAPTCHA / block page
        if len(text) < 200:
            return FetchResult(url, "", method="blocked", blocked=True)
        return FetchResult(url, text, method="browser")
    except Exception:
        return None


def fetch_url(url: str) -> FetchResult:
    """Try all strategies in order, return best result."""

    # 1. Human browser_server — primary path when running (handles any site, real sessions)
    result = _try_browser_server(url)
    if result is not None:
        return result

    # 2. Direct fetch
    result = _direct_fetch(url)
    if result:
        text, raw_html = result
        return FetchResult(url, text, method="direct", raw_html=raw_html)

    # 3. ORCID — if it looks like a researcher profile
    if "orcid.org" in url:
        result = _orcid_fetch(url)
        if result:
            return FetchResult(url, result, method="orcid")

    # 4. Wayback Machine
    result = _wayback_fetch(url)
    if result:
        return FetchResult(url, result, method="wayback")

    # 5. Headless stealth browser
    from .fetcher_browser import fetch_with_browser
    browser_result = fetch_with_browser(url)
    if not browser_result.blocked:
        return browser_result

    # 6. All strategies failed — needs user action
    return FetchResult(url, "", method="blocked", blocked=True)


def fetch_orcid_by_name(name: str) -> FetchResult | None:
    """Search ORCID by name — returns profile text if found."""
    try:
        resp = requests.get(
            "https://pub.orcid.org/v3.0/search/",
            params={"q": f'given-and-family-names:"{name}"', "rows": 3},
            headers={**HEADERS, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get("result", [])
        if not results:
            return None

        orcid_id = results[0].get("orcid-identifier", {}).get("path")
        if not orcid_id:
            return None

        return _fetch_orcid_id(orcid_id)
    except Exception:
        return None


def fetch_text_paste(url: str, pasted_text: str) -> FetchResult:
    """Accept user-pasted text for a blocked URL."""
    return FetchResult(url, pasted_text, method="user_paste")


def _direct_fetch(url: str) -> tuple[str, str] | None:
    """Returns (text, raw_html) or None if blocked."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code in (401, 403, 407, 429):
            return None
        resp.raise_for_status()
        raw = resp.text
        return _extract_text(raw), raw
    except Exception:
        return None


def _wayback_fetch(url: str) -> str | None:
    try:
        # Check if Wayback has a snapshot
        avail = requests.get(
            f"https://archive.org/wayback/available?url={quote_plus(url)}",
            headers=HEADERS, timeout=TIMEOUT,
        )
        avail.raise_for_status()
        snapshot = avail.json().get("archived_snapshots", {}).get("closest", {})
        if not snapshot.get("available"):
            return None

        archived_url = snapshot["url"]
        resp = requests.get(archived_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return _extract_text(resp.text)
    except Exception:
        return None


def _orcid_fetch(url: str) -> str | None:
    try:
        orcid_id = urlparse(url).path.strip("/")
        result = _fetch_orcid_id(orcid_id)
        return result.text if result else None
    except Exception:
        return None


def _fetch_orcid_id(orcid_id: str) -> FetchResult | None:
    try:
        resp = requests.get(
            f"https://pub.orcid.org/v3.0/{orcid_id}/record",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        text = _orcid_to_text(data)
        url = f"https://orcid.org/{orcid_id}"
        return FetchResult(url, text, method="orcid")
    except Exception:
        return None


def _orcid_to_text(data: dict) -> str:
    lines = []
    person = data.get("person", {})

    name = person.get("name", {})
    given = name.get("given-names", {}).get("value", "")
    family = name.get("family-name", {}).get("value", "")
    if given or family:
        lines.append(f"Name: {given} {family}".strip())

    bio = person.get("biography", {})
    if bio and bio.get("content"):
        lines.append(f"Biography: {bio['content']}")

    # Employments
    employments = data.get("activities-summary", {}).get("employments", {}).get("affiliation-group", [])
    for emp in employments[:3]:
        summaries = emp.get("summaries", [])
        for s in summaries:
            org = s.get("employment-summary", {}).get("organization", {}).get("name", "")
            role = s.get("employment-summary", {}).get("role-title", "")
            if org or role:
                lines.append(f"Employment: {role} at {org}".strip(" at"))

    # Works (publications)
    works = data.get("activities-summary", {}).get("works", {}).get("group", [])
    for w in works[:10]:
        ws = w.get("work-summary", [{}])[0]
        title = ws.get("title", {}).get("title", {}).get("value", "")
        year = ws.get("publication-date", {}).get("year", {}).get("value", "")
        if title:
            lines.append(f"Publication ({year}): {title}")

    return "\n".join(lines)


def _extract_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text()) > 60]
        return "\n".join(paras[:20])
    except Exception:
        return html[:2000]
