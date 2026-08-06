"""In-memory + disk session store and shared helpers for the wikimaker API."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.models import PersonProfile
from engine.llm import get_provider
from engine.provenance import classify_source_provenance, evaluate_claim_trust
from engine.notability import score_notability

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

_sessions: dict[str, PersonProfile] = {}
_wiki_statuses: dict[str, dict] = {}

_llm = None


def llm():
    global _llm
    if _llm is None:
        _llm = get_provider()
    return _llm


def _session_path(name: str) -> Path:
    safe = name.replace(" ", "_").replace("/", "_")
    return SESSIONS_DIR / f"{safe}.json"


def _apply_provenance(profile: PersonProfile) -> None:
    source_map = {}
    for s in profile.sources:
        classified = classify_source_provenance(s, profile.name)
        source_map[s.url] = classified

    for i, c in enumerate(profile.claims):
        src = source_map.get(c.source_url) if c.source_url else None
        profile.claims[i] = evaluate_claim_trust(c, src, profile)

    profile.notability = score_notability(profile.name, profile.sources)


def _save_session(name: str) -> None:
    profile = _sessions.get(name)
    if not profile:
        return
    _apply_provenance(profile)
    data = {
        "profile": json.loads(profile.model_dump_json()),
        "wiki_status": _wiki_statuses.get(name, {"status": "clear", "url": None, "note": None}),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _session_path(name).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _load_session_file(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


BROWSER_SERVER = "http://localhost:7070"


def _push_to_browser(url: str) -> bool:
    """Navigate the human browser_server to url. Returns True if browser is running."""
    try:
        from browser_server import _dispatch, _running
        if not _running:
            return False
        _dispatch("navigate", url=url)
        return True
    except Exception:
        return False


def _get_profile(name: str) -> PersonProfile:
    if name not in _sessions:
        raise HTTPException(404, f"No active research session for '{name}'")
    return _sessions[name]


def _check_doi_sources(sources: list, person_name: str, affiliation: str) -> None:
    """In-place: run author check on every source whose URL contains a DOI."""
    from engine.author_check import check_doi_authors, extract_doi
    for source in sources:
        doi = extract_doi(source.url)
        if not doi:
            continue
        result = check_doi_authors(doi, person_name, affiliation)
        source.author_match_status = result["status"]
        source.author_match_name = result["matched_author"]
        source.author_match_affiliation = result["matched_affiliation"]
        source.all_paper_authors = result["all_authors"]
        if result.get("paper_title") and (source.title == source.url or not source.title):
            source.title = result["paper_title"]
