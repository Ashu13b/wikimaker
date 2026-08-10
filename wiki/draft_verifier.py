"""Post-generation verification of a rendered draft.

The checker (`wiki.draft_qa.py`) lints the generated wikitext statically; this
verifier checks the draft against the outside world: live link liveness (plain
requests first, remote-browser page render as an adjudicator) and the parsoid
preview render. It deliberately lives outside `wiki.draft.py` so generation and
verification stay separate concerns.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from engine.provenance import normalize_url


class DraftLink(BaseModel):
    """One external URL referenced by the draft, with a live check result."""
    url: str
    label: str
    archived: bool = False
    status: str = "unknown"
    status_code: int | None = None
    final_url: str | None = None


_REF_OPEN = re.compile(r"<ref(?:\s+name\s*=\s*[\"']([^\"']+)[\"'])?\s*/?>", re.I)
_REF_CLOSE = re.compile(r"</ref>", re.I)
_CITE_FIELD = re.compile(r"\b(archive-url|url|title|website)\s*=\s*([^|\n]+)", re.I)
_EXTERNAL_LINK = re.compile(r"\[(https?://[^\s\[\]]+)(?:\s+([^\]]*?))?\]", re.I)


def extract_draft_links(wikitext: str) -> list[DraftLink]:
    """List the external URLs a draft cites, one entry per ref.

    Prefers the archive-url when a ref has both (the archived copy is what
    readers will actually reach). Reused named refs, duplicate URLs, and
    {{!}}-escaped pipes are handled; results keep wikitext order.
    """
    links: list[DraftLink] = []
    seen: set[str] = set()

    def add(url: str, label: str, archived: bool) -> None:
        norm = normalize_url(url)
        if not norm or norm in seen:
            return
        seen.add(norm)
        links.append(DraftLink(url=url, label=label or url, archived=archived))

    for match in _REF_OPEN.finditer(wikitext):
        close = _REF_CLOSE.search(wikitext, match.end())
        if not close:
            continue
        inner = wikitext[match.end():close.start()].replace("{{!}}", "\x00")
        fields = {m.group(1).lower(): m.group(2).strip().replace("\x00", "|")
                  for m in _CITE_FIELD.finditer(inner)}
        url = fields.get("archive-url") or fields.get("url")
        if url:
            add(url, fields.get("title") or "", bool(fields.get("archive-url")))
            continue
        for m in _EXTERNAL_LINK.finditer(inner):
            add(m.group(1), m.group(2) or "", False)

    for m in _EXTERNAL_LINK.finditer(wikitext):
        add(m.group(1), m.group(2) or "", False)
    return links


def check_draft_links(urls: list[str]) -> dict[str, dict]:
    """Live-check URLs; returns url -> {status, status_code, final_url}.

    status: ok (2xx/3xx) | blocked (401/403/429) | dead (404/410) | unknown.
    Plain requests is the primary, concurrent path (its real-Chrome UA already
    reads most sites correctly). Links requests cannot classify are re-checked
    with a real page render through the remote browser when it is already up —
    the browser context beats requests only where JS/stealth matter, so it is
    used solely as an adjudicator, and only if it is running (never force-
    started for a link check).
    """
    results = _check_links_via_requests(urls)
    uncertain = [u for u, r in results.items() if r["status"] in ("blocked", "unknown")]
    if uncertain:
        try:
            import browser_server as bs
            if bs._running:
                verdict = bs._dispatch(
                    "link_status_page", urls=uncertain, timeout=max(60.0, 20 * len(uncertain)))
                results.update(verdict)
        except Exception:
            pass
    return results


def _check_links_via_requests(urls: list[str]) -> dict[str, dict]:
    from concurrent.futures import ThreadPoolExecutor
    from engine.fetcher import HEADERS
    import requests

    def check_one(url: str) -> dict:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True, stream=True)
            code = resp.status_code
            final = resp.url
            resp.close()
        except requests.RequestException:
            return {"status": "unknown", "status_code": None, "final_url": url}
        if code in (404, 410):
            status = "dead"
        elif code in (401, 403, 429):
            status = "ok" if "web.archive.org" in url or "doi.org/" in url else "blocked"
        elif code == 498 and "web.archive.org" in url:
            status = "ok"
        elif 200 <= code < 400:
            status = "ok"
        else:
            status = "unknown"
        return {"status": status, "status_code": code, "final_url": final}

    with ThreadPoolExecutor(max_workers=6) as pool:
        return dict(zip(urls, pool.map(check_one, urls)))


def render_preview(wikitext: str) -> str:
    """Render wikitext as Wikipedia would, via the parsoid REST transform.

    Returns the HTML body with asset links rewritten to absolute URLs so it
    works inside a sandboxed preview iframe.
    """
    import requests
    from engine.fetcher import BOT_HEADERS

    resp = requests.post(
        "https://en.wikipedia.org/api/rest_v1/transform/wikitext/to/html",
        json={"wikitext": wikitext, "body_only": True, "stash": False},
        headers={"Content-Type": "application/json", "Accept": "text/html", **BOT_HEADERS},
        timeout=30,
    )
    resp.raise_for_status()
    html = resp.text
    html = html.replace('href="/wiki/', 'href="https://en.wikipedia.org/wiki/')
    html = html.replace('href="/w/', 'href="https://en.wikipedia.org/w/')
    html = html.replace('src="//upload.wikimedia.org/', 'src="https://upload.wikimedia.org/')
    html = html.replace('srcset="//upload.wikimedia.org/', 'srcset="https://upload.wikimedia.org/')
    return html
