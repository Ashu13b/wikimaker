"""In-memory + disk session store and shared helpers for the wikimaker API."""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.models import PersonProfile
from engine.llm import get_provider
from engine.provenance import classify_source_provenance, evaluate_claim_trust
from engine.notability import score_notability
from engine.saturation import analyze_research_saturation

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

_sessions: dict[str, PersonProfile] = {}
_wiki_statuses: dict[str, dict] = {}

# FastAPI sync endpoints run in a threadpool, so session reads/mutations/saves
# can interleave. RLock serializes the store-level operations; route handlers
# mutate the shared in-memory profile object (GIL-atomic), then _save_session
# snapshots it under the lock.
_lock = threading.RLock()

_llm = None


def llm():
    global _llm
    if _llm is None:
        _llm = get_provider()
    return _llm


def _new_session_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "session"
    return f"py-{slug}-{secrets.token_hex(4)}"


def _ensure_session_id(profile: PersonProfile) -> str:
    if not profile.session_id:
        profile.session_id = _new_session_id(profile.name)
    return profile.session_id


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _resolve_profile(name_or_id: str) -> PersonProfile | None:
    """Resolve a session by its stable id first, then by display name."""
    with _lock:
        if name_or_id in _sessions:
            return _sessions[name_or_id]
        matches = [p for p in _sessions.values() if p.name == name_or_id]
        if not matches:
            return None
        if len(matches) > 1:
            raise HTTPException(
                409,
                f"Multiple sessions are named '{name_or_id}'. Same-named people cannot "
                f"be told apart by name — resume by session id instead.")
        return matches[0]


def _apply_provenance(profile: PersonProfile) -> None:
    source_map = {}
    for s in profile.sources:
        classified = classify_source_provenance(s, profile.name)
        source_map[s.url] = classified

    for i, c in enumerate(profile.claims):
        src = source_map.get(c.source_url) if c.source_url else None
        profile.claims[i] = evaluate_claim_trust(c, src, profile)

    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    profile.saturation = analyze_research_saturation(profile)


def _save_session(name_or_id: str) -> None:
    import tempfile
    with _lock:
        profile = _resolve_profile(name_or_id)
        if not profile:
            return
        _apply_provenance(profile)
        sid = _ensure_session_id(profile)
        _sessions[sid] = profile
        _wiki_statuses.setdefault(sid, {"status": "clear", "url": None, "note": None})
        data = {
            "profile": json.loads(profile.model_dump_json()),
            "wiki_status": _wiki_statuses.get(sid, {"status": "clear", "url": None, "note": None}),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        target_path = _session_path(sid)
        content = json.dumps(data, indent=2, ensure_ascii=False)
        temp_fd, temp_path = tempfile.mkstemp(dir=SESSIONS_DIR, prefix=f".{sid}-", suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, target_path)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise


def _load_session_file(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


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


def _get_profile(name_or_id: str) -> PersonProfile:
    profile = _resolve_profile(name_or_id)
    if profile is None:
        raise HTTPException(404, f"No active research session for '{name_or_id}'")
    return profile


def _identity_matches(profile_dict: dict, name: str, wikidata_id: str | None) -> bool:
    """Same display name AND a matching identity hint (wikidata equal, or neither)."""
    if profile_dict.get("name") != name:
        return False
    existing_wd = profile_dict.get("wikidata_id")
    if wikidata_id and existing_wd:
        return wikidata_id == existing_wd
    return not wikidata_id and not existing_wd


def _activate_session(profile: PersonProfile, wiki_status: dict) -> PersonProfile:
    """Key an in-memory profile by its stable id and reconcile resume-time state."""
    from engine.relevance import flag_sources
    from engine.extractor import find_missing_slots
    from engine.researcher_ids import extract_ids_from_sources

    with _lock:
        flag_sources(profile.sources, profile.name, profile.field or "", profile.affiliation or "")
        profile.missing_slots = find_missing_slots(profile, profile.claims)
        for id_type, id_val in extract_ids_from_sources(profile.sources).items():
            profile.researcher_ids.setdefault(id_type, id_val)
        _apply_provenance(profile)
        sid = _ensure_session_id(profile)
        _sessions[sid] = profile
        _wiki_statuses[sid] = wiki_status
        return profile


def _find_session_on_disk(pred) -> tuple[dict, Path] | None:
    """Return the first session file whose profile satisfies pred, if any."""
    for path in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = _load_session_file(path)
        if not data:
            continue
        if pred(data.get("profile", {})):
            return data, path
    return None


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
