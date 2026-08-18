"""Multi-strategy URL fetcher with fallbacks for blocked sources."""
from __future__ import annotations
import ipaddress
import re
import socket
import requests
from urllib.parse import quote_plus, urlparse

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
BOT_HEADERS = {"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)"}  # for APIs that want bot UA
TIMEOUT = 10
MAX_FETCH_BYTES = 5 * 1024 * 1024  # 5 MB maximum response body

# Bot-wall / challenge signatures, shared by the headless fetcher and the remote
# browser's wall detection so the two vocabularies can't drift apart.
BOT_WALL_RE = re.compile(
    r"captcha|cf-browser-verification|just a moment|access denied|"
    r"unusual activity|please verify|verify you are human|enable javascript|"
    r"403 forbidden", re.I)


def is_safe_public_url(url: str) -> bool:
    """Verify url uses http/https and does not resolve to private/loopback/cloud-metadata IP."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname_lower = hostname.lower()
        if hostname_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        try:
            ip = ipaddress.ip_address(hostname_lower)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
            return True
        except ValueError:
            pass

        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for family, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    return False
        except socket.gaierror:
            pass
        return True
    except Exception:
        return False


def check_liveness(url: str) -> tuple[str, str | None]:
    """Return (liveness, archive_url) for a URL.

    liveness: alive | blocked | dead | unknown
    - dead (404/410) also looks up a Wayback snapshot to use as the citation.
    - blocked (403/401/429) is bot-protection: still citable by a human.
    """
    if not is_safe_public_url(url):
        return "unknown", None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True, stream=True)
        code = resp.status_code
    except requests.RequestException:
        return "unknown", None
    if code in (404, 410):
        return "dead", get_wayback_url(url)
    if code in (401, 403, 429):
        return "blocked", None
    if 200 <= code < 400:
        return "alive", None
    return "unknown", None


def get_wayback_url(url: str) -> str | None:
    """Return the closest Wayback snapshot URL for a dead page, or None."""
    try:
        resp = requests.get("https://archive.org/wayback/available",
                            params={"url": url}, headers=HEADERS, timeout=10)
        snapshot = resp.json().get("archived_snapshots", {}).get("closest", {})
        return snapshot.get("url") or None
    except Exception:
        return None


class FetchResult:
    def __init__(self, url: str, text: str, method: str, blocked: bool = False, raw_html: str = "", final_url: str = ""):
        self.url = url
        self.text = text          # extracted text content (paragraphs only)
        self.raw_html = raw_html  # full HTML — for link extraction in crawler
        self.method = method      # direct | wayback | orcid | blocked
        self.blocked = blocked    # True = needs user paste or screenshot
        self.final_url = final_url  # URL the page really loaded at (after redirects), "" if unknown


# The remote browser is mounted at /browser on the unified server (port 3890);
# the legacy standalone server ran on 7070. Probe whichever responds.
_BROWSER_BASES = ("http://localhost:3890/browser", "http://localhost:7070")


def _try_browser_server(url: str) -> FetchResult | None:
    """Fetch via the human browser_server if it's running. Returns None if unavailable."""
    base = None
    for candidate in _BROWSER_BASES:
        try:
            if requests.get(f"{candidate}/status", timeout=1).json().get("running"):
                base = candidate
                break
        except Exception:
            continue
    if not base:
        return None
    try:
        nav = requests.post(f"{base}/navigate", json={"url": url}, timeout=30).json()
        if nav.get("error"):
            return None
        data = requests.get(f"{base}/content", timeout=5).json()
        text = data.get("text", "").strip()
        # Treat short content as possible CAPTCHA / block page
        if len(text) < 200:
            return FetchResult(url, "", method="blocked", blocked=True)
        return FetchResult(url, text, method="browser", final_url=data.get("url", ""))
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
        text, raw_html, final_url = result
        return FetchResult(url, text, method="direct", raw_html=raw_html, final_url=final_url)

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


def _direct_fetch(url: str) -> tuple[str, str, str] | None:
    """Returns (text, raw_html, final_url) or None if blocked or unsafe."""
    if not is_safe_public_url(url):
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True)
        if resp.status_code in (401, 403, 407, 429):
            return None
        resp.raise_for_status()

        if resp.url != url and not is_safe_public_url(resp.url):
            return None

        content_parts = []
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=65536):
            content_parts.append(chunk)
            downloaded += len(chunk)
            if downloaded > MAX_FETCH_BYTES:
                break
        raw_bytes = b"".join(content_parts)

        ct = resp.headers.get("content-type", "")
        if "application/pdf" in ct or url.lower().split("?")[0].endswith(".pdf"):
            text = _pdf_extract(raw_bytes)
            return text, "", resp.url  # no raw HTML for PDFs
        encoding = resp.encoding or "utf-8"
        raw = raw_bytes.decode(encoding, errors="replace")
        return _extract_text(raw), raw, resp.url
    except Exception:
        return None


def _pdf_extract(data: bytes) -> str:
    """Extract text from PDF bytes — tries pdfminer.six first, falls back to pypdf."""
    # pdfminer.six
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams
        import io
        out = io.StringIO()
        extract_text_to_fp(io.BytesIO(data), out, laparams=LAParams())
        text = out.getvalue().strip()
        if text:
            return text[:8000]
    except Exception:
        pass
    # pypdf fallback
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages[:20]]
        text = "\n".join(pages).strip()
        if text:
            return text[:8000]
    except Exception:
        pass
    return ""


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
