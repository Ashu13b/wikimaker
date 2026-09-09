"""Session lifecycle routes (load, resume, delete)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from . import store

from engine.models import PersonProfile
from engine.extractor import extract_claims

sessions_router = APIRouter()

@sessions_router.post("/sessions/resume")
def resume_session(body: dict) -> dict:
    """Load a saved session from disk into memory and return it."""
    filename = body.get("file") or body.get("session_id")
    if not filename or not isinstance(filename, str):
        raise HTTPException(400, "file or session_id required")
    filename = filename.strip()
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid session reference")

    sessions_root = store.SESSIONS_DIR.resolve()
    # Bare session ids are resolved to their file.
    path = (store.SESSIONS_DIR / filename).resolve()
    if not path.is_relative_to(sessions_root):
        raise HTTPException(400, "Invalid session reference")

    if not path.exists() and not filename.endswith(".json"):
        path = store._session_path(filename).resolve()
        if not path.is_relative_to(sessions_root):
            raise HTTPException(400, "Invalid session reference")
    if not path.exists():
        raise HTTPException(404, f"Session file not found: {filename}")
    data = store._load_session_file(path)
    if not data:
        raise HTTPException(500, "Could not read session file")

    profile = PersonProfile(**data["profile"])
    wiki_status = data.get("wiki_status", {"status": "clear", "url": None, "note": None})

    # Re-check Wikimedia status on resume so the workspace routes to reality
    # (an article or draft may have been created since the session was saved)
    # instead of trusting a stale stored status. Keep the stored value if the
    # check fails (e.g. offline).
    try:
        from wiki.wiki_check import check_existing_page, check_title_for
        wiki_status = check_existing_page(
            check_title_for(profile.name, profile.wikipedia_url)).model_dump()
    except Exception:
        pass

    # If session has sources but no claims (was saved before LLM was available), re-extract now
    # Never repopulate a session from the stub provider: its extracted claims are fabricated.
    if profile.sources and not profile.claims:
        from engine.llm import has_real_llm
        if has_real_llm():
            profile.claims = extract_claims(profile, profile.sources, store.llm())

    profile = store._activate_session(profile, wiki_status)
    sid = store._ensure_session_id(profile)
    store._save_session(sid)

    # Migrate legacy name-based files to the stable id filename.
    id_path = store._session_path(sid).resolve()
    if path != id_path and id_path.exists() and path.is_relative_to(sessions_root):
        path.unlink()

    return {
        "profile": profile.model_dump(),
        "wiki_status": store._wiki_statuses.get(sid),
    }


@sessions_router.get("/sessions")
def list_sessions() -> dict:
    """List all saved research sessions from disk."""
    sessions = []
    for path in sorted(store.SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = store._load_session_file(path)
        if not data:
            continue
        profile = data.get("profile", {})
        notability = profile.get("notability") or {}
        sessions.append({
            "id": profile.get("session_id"),
            "name": profile.get("name", path.stem.replace("_", " ")),
            "field": profile.get("field"),
            "affiliation": profile.get("affiliation"),
            "photo_url": profile.get("photo_url"),
            "source_count": len(profile.get("sources", [])),
            "claim_count": len(profile.get("claims", [])),
            "notability_label": notability.get("label", "Unknown"),
            "notability_score": notability.get("score", 0),
            "saved_at": data.get("saved_at"),
            "file": path.name,
        })
    return {"sessions": sessions}




@sessions_router.delete("/sessions/{ref}")
def delete_session(ref: str) -> dict:
    """Delete a saved session and remove it from memory.

    Accepts a session id (py-...) or a session file name (legacy or id-based).
    """
    if "/" in ref or "\\" in ref or ".." in ref:
        raise HTTPException(400, "Invalid session reference")
    sessions_root = store.SESSIONS_DIR.resolve()
    sid = ref[:-5] if ref.endswith(".json") else ref

    profile = store._resolve_profile(sid)
    if profile is None:
        # Not loaded — resolve the file on disk directly.
        path = (store.SESSIONS_DIR / ref if ref.endswith(".json") else store._session_path(sid)).resolve()
        if not path.is_relative_to(sessions_root):
            raise HTTPException(400, "Invalid session reference")
        if not path.exists():
            raise HTTPException(404, f"Session not found: {ref}")
        data = store._load_session_file(path)
        if not data:
            raise HTTPException(500, "Could not read session file")
    else:
        sid = store._ensure_session_id(profile)
        path = store._session_path(sid).resolve()
        if not path.is_relative_to(sessions_root):
            raise HTTPException(400, "Invalid session reference")

    store._sessions.pop(sid, None)
    store._wiki_statuses.pop(sid, None)
    if path.exists() and path.is_relative_to(sessions_root):
        path.unlink()
    return {"deleted": ref}




