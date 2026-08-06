"""Session lifecycle routes (load, resume, delete)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from . import store

from engine.models import PersonProfile
from engine.extractor import extract_claims, find_missing_slots
from engine.relevance import flag_sources
from engine.researcher_ids import extract_ids_from_sources

sessions_router = APIRouter()

@sessions_router.post("/sessions/resume")
def resume_session(body: dict) -> dict:
    """Load a saved session from disk into memory and return it."""
    filename = body.get("file")
    if not filename:
        raise HTTPException(400, "file required")
    path = store.SESSIONS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Session file not found: {filename}")
    data = store._load_session_file(path)
    if not data:
        raise HTTPException(500, "Could not read session file")

    profile = PersonProfile(**data["profile"])
    wiki_status = data.get("wiki_status", {"status": "clear", "url": None, "note": None})

    # If session has sources but no claims (was saved before LLM was available), re-extract now
    # Never repopulate a session from the stub provider: its extracted claims are fabricated.
    if profile.sources and not profile.claims:
        from engine.llm import has_real_llm
        if has_real_llm():
            profile.claims = extract_claims(profile, profile.sources, store.llm())
    flag_sources(profile.sources, profile.name, profile.field or "", profile.affiliation or "")
    profile.missing_slots = find_missing_slots(profile, profile.claims)

    # Rescan source URLs for researcher IDs missed by older sessions
    found_ids = extract_ids_from_sources(profile.sources)
    for id_type, id_val in found_ids.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    store._sessions[profile.name] = profile
    store._wiki_statuses[profile.name] = wiki_status
    store._save_session(profile.name)

    return {
        "profile": profile.model_dump(),
        "wiki_status": wiki_status,
    }


