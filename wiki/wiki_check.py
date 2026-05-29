"""Check Wikipedia for existing pages, draft history, and deletion logs."""
from __future__ import annotations
import requests
from pydantic import BaseModel
from typing import Optional

HEADERS = {"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)"}
WIKI_API = "https://en.wikipedia.org/w/api.php"


class WikiStatus(BaseModel):
    status: str  # exists | draft | deleted | clear
    url: Optional[str] = None
    note: Optional[str] = None


def check_existing_page(title: str) -> WikiStatus:
    if _page_exists(title):
        return WikiStatus(
            status="exists",
            url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
            note="A Wikipedia article already exists for this person.",
        )
    if _page_exists(f"Draft:{title}"):
        return WikiStatus(
            status="draft",
            url=f"https://en.wikipedia.org/wiki/Draft:{title.replace(' ', '_')}",
            note="A draft already exists for this person at AfC.",
        )
    deleted = _deletion_note(title)
    if deleted:
        return WikiStatus(status="deleted", note=f"Previously deleted: {deleted}")
    return WikiStatus(status="clear")


def _page_exists(title: str) -> bool:
    try:
        resp = requests.get(WIKI_API, params={
            "action": "query", "titles": title, "format": "json",
        }, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        return "-1" not in pages
    except Exception:
        return False


def _deletion_note(title: str) -> str | None:
    try:
        resp = requests.get(WIKI_API, params={
            "action": "query", "list": "logevents",
            "letype": "delete", "letitle": title,
            "lelimit": "1", "format": "json",
        }, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        events = resp.json().get("query", {}).get("logevents", [])
        if not events:
            return None
        e = events[0]
        return f"{e.get('action', 'deleted')} on {e.get('timestamp', '')[:10]}"
    except Exception:
        return None
