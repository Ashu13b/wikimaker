"""Draft generation, preview, links, and QA routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from . import store

from .schemas import DraftRequest

from wiki.wiki_check import draft_generation_allowed
from wiki.draft import audit_profile, render_draft
from wiki.draft_hi import render_hindi_draft

draft_router = APIRouter()

@draft_router.get("/draft/audit/{name}")
def draft_audit(name: str) -> dict:
    """Return server-computed draft readiness without generating text."""
    audit = audit_profile(store._get_profile(name))
    return {"audit": audit.model_dump(exclude={"evidence"})}


@draft_router.post("/draft")
def generate_draft(req: DraftRequest) -> dict:
    """Generate and persist a deterministic draft from the server-owned session."""
    profile = store._get_profile(req.profile_name)
    sid = store._ensure_session_id(profile)
    wiki_status = store._wiki_statuses.get(sid) or store._wiki_statuses.get(profile.name, {"status": "clear"})
    status = wiki_status.get("status", "clear")
    if not draft_generation_allowed(status):
        if status == "exists":
            detail = "An article already exists. Prepare improvements instead of a duplicate draft."
        else:
            detail = "A prior deletion must be reviewed before generating another draft."
        raise HTTPException(409, detail)

    audit = audit_profile(profile)
    if not audit.ready:
        raise HTTPException(422, {
            "message": "The evidence audit found blockers.",
            "audit": audit.model_dump(exclude={"evidence"}),
        })

    profile.wikitext_en = render_draft(profile, audit)
    try:
        profile.wikitext_hi = render_hindi_draft(profile, audit)
    except Exception:
        profile.wikitext_hi = None
    store._save_session(profile)
    return {
        "profile": profile.model_dump(),
        "audit": audit.model_dump(exclude={"evidence"}),
    }


@draft_router.post("/draft/links")
def draft_links(body: dict) -> dict:
    """List every external URL the draft cites, live-checked."""
    profile = store._get_profile(body["profile_name"])
    if not profile.wikitext_en:
        raise HTTPException(400, "No draft has been generated yet.")
    from wiki.draft_verifier import extract_draft_links, check_draft_links

    links = extract_draft_links(profile.wikitext_en)
    if links:
        checked = check_draft_links([link.url for link in links])
        for link in links:
            result = checked.get(link.url, {})
            link.status = result.get("status", "unknown")
            link.status_code = result.get("status_code")
            link.final_url = result.get("final_url")
    return {"links": [link.model_dump() for link in links]}


@draft_router.post("/draft/preview")
def draft_preview(body: dict) -> dict:
    """Render the draft's wikitext exactly as Wikipedia would display it."""
    profile = store._get_profile(body["profile_name"])
    if not profile.wikitext_en:
        raise HTTPException(400, "No draft has been generated yet.")
    from wiki.draft_verifier import render_preview

    try:
        html = render_preview(profile.wikitext_en)
    except Exception as exc:
        raise HTTPException(502, f"Wikipedia preview renderer unavailable: {exc}")
    return {"html": html}


@draft_router.post("/draft/qa")
def draft_qa(body: dict) -> dict:
    """Lint the stored draft against AfC review criteria."""
    profile = store._get_profile(body["profile_name"])
    if not profile.wikitext_en:
        raise HTTPException(400, "No draft has been generated yet.")
    from wiki.draft_qa import qa_draft

    report = qa_draft(profile)
    return {
        "findings": [f.model_dump() for f in report.findings],
        "passed": report.passed,
        "counts": report.counts,
    }


@draft_router.post("/draft/verify")
def draft_verify(body: dict) -> dict:
    """Post-generation verification: run the checker (QA lint) and the verifier
    (live link liveness) on the stored draft and return one combined result."""
    profile = store._get_profile(body["profile_name"])
    if not profile.wikitext_en:
        raise HTTPException(400, "No draft has been generated yet.")
    from wiki.draft_qa import qa_draft
    from wiki.draft_verifier import extract_draft_links, check_draft_links

    qa = qa_draft(profile)
    links = extract_draft_links(profile.wikitext_en)
    if links:
        checked = check_draft_links([link.url for link in links])
        for link in links:
            result = checked.get(link.url, {})
            link.status = result.get("status", "unknown")
            link.status_code = result.get("status_code")
            link.final_url = result.get("final_url")

    return {
        "qa": {
            "passed": qa.passed,
            "counts": qa.counts,
            "findings": [f.model_dump() for f in qa.findings],
        },
        "links": [link.model_dump() for link in links],
        "verified": qa.passed and all(link.status == "ok" for link in links),
    }


