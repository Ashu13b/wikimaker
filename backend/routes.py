"""FastAPI routes for the wikimaker API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .schemas import (
    IdentifyRequest, ResearchRequest, AddSourceRequest, AddDocumentFact,
    AddSourcedClaimRequest, VerifyClaimRequest, AddSourcePaste, CrawlRequest,
    TargetedSearchRequest, DraftRequest, FindIdsRequest, RefreshPapersRequest,
)
from . import store
from . import pipelines
from .routes_sessions import sessions_router, resume_session  # noqa: F401

from engine.models import PersonProfile, Claim, VerificationState
from engine.researcher import (
    fetch_auto_sources, fetch_url_source, fetch_url_source_with_paste,
    fetch_institution_sources, targeted_slot_search,
)
from engine.classifier import classify_sources
from engine.notability import score_notability
from engine.extractor import extract_claims, find_missing_slots
from engine.relevance import flag_sources
from engine.crawler import crawl
from engine.researcher_ids import (
    extract_ids_from_sources, is_sd_article_url, is_sd_author_url,
)
from engine.provenance import normalize_url
from wiki.wiki_check import check_existing_page, draft_generation_allowed
from wiki.draft import audit_profile, render_draft

router = APIRouter()
router.include_router(sessions_router)

# Endpoints ──────────────────────────────────────────────────────────────────────────

@router.post("/identify")
def identify(req: IdentifyRequest) -> dict:
    """Quick web search preview to confirm we're researching the right person."""
    from engine.researcher import _google_cse, _duckduckgo_html
    sources = _google_cse(req.name, req.field, req.affiliation) or _duckduckgo_html(req.name, req.field, req.affiliation)
    results = [
        {"title": s.title, "url": s.url, "snippet": s.snippet, "publisher": s.publisher}
        for s in sources[:5]
    ]
    return {"results": results}


@router.post("/research/start")
def research_start(req: ResearchRequest) -> dict:
    """Initialize session, run wiki check, fetch + classify sources, score notability."""
    wiki_status = check_existing_page(req.name)

    # Never choose a Wikidata image from a name alone: same-name people are
    # common. Enrich from Wikidata only when the user confirmed a specific QID.
    photo_url = req.photo_url
    if not photo_url and req.wikidata_id:
        from engine.identifier import fetch_wikidata_photo_by_id
        photo_url = fetch_wikidata_photo_by_id(req.wikidata_id)

    profile = PersonProfile(
        name=req.name,
        wikidata_id=req.wikidata_id,
        wikipedia_url=req.wikipedia_url,
        photo_url=photo_url,
        field=req.field,
        affiliation=req.affiliation,
        nationality=req.nationality,
        birth_date=req.birth_year,
    )

    sources, s2_author_id = fetch_auto_sources(req.name, req.field, req.affiliation)
    if s2_author_id:
        profile.researcher_ids["semantic_scholar"] = s2_author_id

    # Extract researcher IDs from existing source URLs
    found_ids = extract_ids_from_sources(sources)
    for id_type, id_val in found_ids.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    # If affiliation is known, crawl the institution website for biographical sources
    if req.affiliation:
        institution_sources = fetch_institution_sources(req.name, req.affiliation)
        existing_urls = {s.url for s in sources}
        sources.extend(s for s in institution_sources if s.url not in existing_urls)

    sources = classify_sources(sources, store.llm())
    store._check_doi_sources(sources, req.name, req.affiliation or "")
    flag_sources(sources, req.name, req.field or "", req.affiliation or "")
    # Drop wrong-person sources before saving — keep uncertain ones (may be right, user can judge)
    sources = [s for s in sources if s.relevance_flag != "likely_wrong"]
    profile.sources = sources
    # Do not extract claims or score notability until the user verifies sources!
    profile.claims = []
    profile.notability = score_notability(req.name, [])
    profile.missing_slots = find_missing_slots(profile, [])

    store._sessions[req.name] = profile
    store._wiki_statuses[req.name] = wiki_status.model_dump()
    store._save_session(req.name)

    return {
        "wiki_status": wiki_status.model_dump(),
        "notability": profile.notability.model_dump(),
        "profile": profile.model_dump(),
    }


@router.post("/research/add-source")
def add_source(req: AddSourceRequest) -> dict:
    """User pastes a URL — fetch it, classify it, extract claims from it.

    Special cases:
    - ScienceDirect article URL: resolved via PII→CrossRef→OpenAlex pipeline
    - ScienceDirect author URL: Scopus ID extracted, stored in researcher_ids
    """
    profile = store._get_profile(req.profile_name)
    url = req.url

    if any(s.url == url for s in profile.sources):
        raise HTTPException(400, "This source is already in your list.")

    # ── ScienceDirect article: use PII pipeline instead of fetching ───────────
    if is_sd_article_url(url):
        return pipelines._add_sd_article(profile, url)

    # ── ScienceDirect author profile: extract Scopus ID + fetch OpenAlex works ─
    if is_sd_author_url(url):
        return pipelines._add_sd_author_profile(profile, url)

    # ── Normal URL fetch ──────────────────────────────────────────────────────
    source, blocked = fetch_url_source(url, profile.name)
    [source] = classify_sources([source], store.llm())
    flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    store._check_doi_sources([source], profile.name, profile.affiliation or "")
    source.liveness = "blocked" if blocked else "alive"

    # Extract researcher IDs from the new URL (e.g. user pastes an ORCID link)
    new_ids = extract_ids_from_sources([source])
    for id_type, id_val in new_ids.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    if url in profile.rejected_sources:
        profile.rejected_sources.remove(url)
    if url in profile.skipped_sources:
        profile.skipped_sources.remove(url)

    profile.sources.append(source)
    # Claims are extracted on confirmation, not on add
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)

    # If blocked, push to human browser_server if it's running
    sent_to_browser = False
    if blocked:
        sent_to_browser = store._push_to_browser(url)

    return {
        "source": source.model_dump(),
        "blocked": blocked,
        "sent_to_browser": sent_to_browser,
        "new_claims": [],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@router.post("/research/add-document-fact")
def add_document_fact(req: AddDocumentFact) -> dict:
    """User types a fact from a document — no URL, timeline-only, marked unsourced."""
    profile = store._get_profile(req.profile_name)
    claim = Claim(
        text=req.text,
        field=req.field,
        source_url=None,          # no web source
        verification=VerificationState.unverified,
        user_provided=True,
        auto_source_attempted=False,
    )
    profile.claims.append(claim)
    return {"claim": claim.model_dump()}


@router.post("/research/add-sourced-claim")
def add_sourced_claim(req: AddSourcedClaimRequest) -> dict:
    """Bind a fact the user read in a source to that source's URL.

    The source must already be in the session. The claim is created confirmed and
    user-provided; draft approval remains a separate explicit action, so a fact
    cannot enter the draft until the user both verifies the source and approves it.
    """
    profile = store._get_profile(req.profile_name)
    if not any(s.url == req.url for s in profile.sources):
        raise HTTPException(400, "Source URL is not in this session; add the source first.")
    claim = Claim(
        text=req.text,
        field=req.field,
        source_url=req.url,
        verification=VerificationState.confirmed,
        user_provided=True,
        date_context=req.date_context,
    )
    source = next(s for s in profile.sources if s.url == req.url)
    from engine.provenance import evaluate_claim_trust
    claim = evaluate_claim_trust(claim, source, profile)
    profile.claims.append(claim)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)
    return {
        "claim": claim.model_dump(),
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@router.post("/research/verify-claim")
def verify_claim(name: str, req: VerifyClaimRequest) -> dict:
    profile = store._get_profile(name)
    if req.claim_index >= len(profile.claims):
        raise HTTPException(400, "claim_index out of range")

    claim = profile.claims[req.claim_index]
    if req.action == "confirm":
        claim.verification = VerificationState.confirmed
    elif req.action == "edit" and req.edited_text:
        claim.text = req.edited_text
        claim.verification = VerificationState.edited
        claim.draft_approved = False
        claim.draft_text = None
    elif req.action == "skip":
        claim.verification = VerificationState.skipped
        claim.draft_approved = False
        claim.draft_text = None
    elif req.action == "approve_draft":
        if claim.verification not in {VerificationState.confirmed, VerificationState.edited}:
            raise HTTPException(400, "Confirm the claim before approving it for the draft")
        source = next((source for source in profile.sources if source.url == claim.source_url), None)
        if source is None or not source.human_verified:
            raise HTTPException(400, "Draft claims require a human-verified source")
        claim.draft_approved = True
        claim.draft_text = req.edited_text or claim.text
    elif req.action == "remove_draft":
        claim.draft_approved = False
        claim.draft_text = None
    else:
        raise HTTPException(400, f"Unsupported claim action: {req.action}")

    store._save_session(name)
    return {"claim": claim.model_dump()}


@router.post("/research/add-source-paste")
def add_source_paste(req: AddSourcePaste) -> dict:
    """User pasted text from a blocked page (or typed from a screenshot/PDF)."""
    profile = store._get_profile(req.profile_name)
    source = fetch_url_source_with_paste(req.url, req.pasted_text)
    [source] = classify_sources([source], store.llm())
    flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    source.human_verified = True
    new_claims = extract_claims(profile, [source], store.llm())
    profile.sources.append(source)
    profile.claims.extend(new_claims)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)
    return {
        "source": source.model_dump(),
        "new_claims": [c.model_dump() for c in new_claims],
        "notability": profile.notability.model_dump(),
    }


@router.post("/research/crawl")
def deep_crawl(req: CrawlRequest) -> dict:
    """Start from seed URLs and crawl outward — follow links to find more sources."""
    profile = store._get_profile(req.profile_name)
    keywords = req.keywords or [profile.field or "", profile.affiliation or ""]
    keywords = [k for k in keywords if k]

    graph = crawl(
        seed_urls=req.seed_urls,
        person_name=profile.name,
        keywords=keywords,
        max_nodes=req.max_nodes,
        max_depth=req.max_depth,
    )

    new_sources = graph.to_sources(None)
    new_sources = classify_sources(new_sources, store.llm())

    # Only keep sources that mention the person at least once and are not rejected/skipped
    existing_urls = {s.url for s in profile.sources}
    rejected_urls = set(getattr(profile, "rejected_sources", []) or [])
    skipped_urls = set(getattr(profile, "skipped_sources", []) or [])
    excluded = existing_urls | rejected_urls | skipped_urls

    relevant = [
        s for s in new_sources
        if graph.relevance_hits.get(s.url, 0) > 0 and s.url not in excluded
    ]

    new_claims = []
    profile.sources.extend(relevant)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)

    return {
        "nodes_crawled": len(graph.nodes),
        "relevant_sources": len(relevant),
        "new_claims": len(new_claims),
        "notability": profile.notability.model_dump(),
        "sources": [s.model_dump() for s in relevant],
    }


@router.post("/research/targeted-search")
def targeted_search_endpoint(req: TargetedSearchRequest) -> dict:
    """Search for sources likely to fill a specific Wikipedia slot."""
    profile = store._get_profile(req.profile_name)
    sources = targeted_slot_search(
        person_name=profile.name,
        slot=req.slot,
        field=profile.field,
        affiliation=profile.affiliation,
        hint=req.hint,
    )
    # Deduplicate against existing, rejected, or skipped sources
    existing_urls = {s.url for s in profile.sources}
    rejected_urls = set(getattr(profile, "rejected_sources", []) or [])
    skipped_urls = set(getattr(profile, "skipped_sources", []) or [])
    excluded = existing_urls | rejected_urls | skipped_urls

    new_sources = [s for s in sources if s.url not in excluded]
    new_sources = classify_sources(new_sources, store.llm())
    flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
    # Auto-added search results must be citable: never flood the session with
    # self-published or unreliable noise (LinkedIn dir pages, personal trainers, etc.)
    new_sources = [
        s for s in new_sources
        if s.reliability.value not in ("self_published", "unreliable")
    ]
    new_claims = []
    profile.sources.extend(new_sources)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)

    return {
        "sources": [s.model_dump() for s in new_sources],
        "new_claims": [c.model_dump() for c in new_claims],
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump(),
    }


@router.post("/research/auto-enrich")
def auto_enrich_endpoint(body: dict) -> dict:
    """Autonomous discovery loop — inspects missing slots and recursively iterates search queries."""
    profile_name = body["profile_name"]
    profile = store._get_profile(profile_name)
    missing = profile.missing_slots or find_missing_slots(profile, profile.claims)

    existing_urls = {s.url for s in profile.sources}
    rejected_urls = set(getattr(profile, "rejected_sources", []) or [])
    skipped_urls = set(getattr(profile, "skipped_sources", []) or [])
    excluded = existing_urls | rejected_urls | skipped_urls

    added_sources = []
    added_claims = []
    max_slots = 8
    max_sources = 15

    # Iterate through missing slots and execute targeted multi-query search
    for slot in missing[:max_slots]:
        if len(added_sources) >= max_sources:
            break
        candidate_sources = targeted_slot_search(
            person_name=profile.name,
            slot=slot,
            field=profile.field,
            affiliation=profile.affiliation,
        )
        new_sources = [s for s in candidate_sources if s.url not in excluded][: max_sources - len(added_sources)]
        if new_sources:
            new_sources = classify_sources(new_sources, store.llm())
            flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
            new_sources = [
                s for s in new_sources
                if s.reliability.value not in ("self_published", "unreliable")
            ]
            new_claims = extract_claims(profile, new_sources, store.llm())

            profile.sources.extend(new_sources)
            profile.claims.extend(new_claims)
            excluded.update(s.url for s in new_sources)
            added_sources.extend(new_sources)
            added_claims.extend(new_claims)

    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)

    return {
        "ok": True,
        "added_source_count": len(added_sources),
        "added_claim_count": len(added_claims),
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump(),
    }


@router.get("/draft/audit/{name}")
def draft_audit(name: str) -> dict:
    """Return server-computed draft readiness without generating text."""
    audit = audit_profile(store._get_profile(name))
    return {"audit": audit.model_dump(exclude={"evidence"})}


@router.post("/draft")
def generate_draft(req: DraftRequest) -> dict:
    """Generate and persist a deterministic draft from the server-owned session."""
    profile = store._get_profile(req.profile_name)
    wiki_status = store._wiki_statuses.get(profile.name, {"status": "clear"})
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
    profile.wikitext_hi = None
    store._save_session(profile.name)
    return {
        "profile": profile.model_dump(),
        "audit": audit.model_dump(exclude={"evidence"}),
    }

@router.get("/session/{name}")
def get_session(name: str) -> dict:
    return {"profile": store._get_profile(name).model_dump()}


@router.post("/research/source/verify")
def verify_source(body: dict) -> dict:
    """Mark a source as human-verified. On verify, extract claims from it."""
    profile = store._get_profile(body["profile_name"])
    url = body["url"]
    verified = body.get("verified", True)
    source = next((s for s in profile.sources if s.url == url), None)
    if not source:
        return {"ok": True, "new_claims": [], "missing_slots": profile.missing_slots}

    source.human_verified = verified
    norm_target = normalize_url(url)
    new_claims: list = []

    if verified:
        # Liveness + Wayback fallback at the moment of human confirmation.
        from engine.fetcher import check_liveness
        source.liveness, source.archive_url = check_liveness(url)

    if verified and source.relevance_flag != "likely_wrong":
        existing_for_url = [c for c in profile.claims if c.source_url and normalize_url(c.source_url) == norm_target]
        if not existing_for_url:
            extracted = extract_claims(profile, [source], store.llm())
            if extracted:
                profile.claims.extend(extracted)
                profile.missing_slots = find_missing_slots(profile, profile.claims)
                new_claims = extracted
        else:
            new_claims = existing_for_url

    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)
    return {
        "ok": True,
        "new_claims": [c.model_dump() for c in new_claims],
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@router.post("/research/source/reject")
def reject_source(body: dict) -> dict:
    """Remove a source and all claims extracted from it."""
    profile = store._get_profile(body["profile_name"])
    url = body["url"]
    profile.sources = [s for s in profile.sources if s.url != url]
    removed = [c for c in profile.claims if c.source_url == url]
    profile.claims = [c for c in profile.claims if c.source_url != url]
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)
    return {
        "removed_claim_count": len(removed),
        "notability": profile.notability.model_dump(),
        "sources": [s.model_dump() for s in profile.sources],
        "claims": [c.model_dump() for c in profile.claims],
    }


@router.get("/sessions")
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


@router.delete("/sessions/{filename}")
def delete_session(filename: str) -> dict:
    """Delete a saved session file and remove from in-memory cache."""
    if "/" in filename or "\\" in filename or not filename.endswith(".json"):
        raise HTTPException(400, "Invalid filename")
    path = store.SESSIONS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Session file not found: {filename}")
    # Derive person name from file to evict in-memory session
    data = store._load_session_file(path)
    if data:
        person_name = data.get("profile", {}).get("name")
        if person_name and person_name in store._sessions:
            del store._sessions[person_name]
        if person_name and person_name in store._wiki_statuses:
            del store._wiki_statuses[person_name]
    path.unlink()
    return {"deleted": filename}




@router.post("/research/find-researcher-ids")
def find_researcher_ids_endpoint(req: FindIdsRequest) -> dict:
    """Search for ORCID, Google Scholar, Scopus, ResearchGate IDs and validate ORCID."""
    from engine.researcher_ids import search_researcher_ids, validate_orcid
    profile = store._get_profile(req.profile_name)
    found = search_researcher_ids(profile.name, profile.field, profile.affiliation)
    for id_type, id_val in found.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    # ORCID candidates are cheap to validate and unsafe to retain on a name hit
    # alone: coauthors and namesakes commonly appear in the same search results.
    orcid_id = profile.researcher_ids.get("orcid")
    if orcid_id and not profile.confirmed_ids.get("orcid"):
        valid = validate_orcid(orcid_id, profile.name, profile.affiliation)
        profile.confirmed_ids["orcid"] = valid
        if not valid:
            profile.researcher_ids.pop("orcid", None)

    store._save_session(profile.name)
    return {
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@router.post("/research/refresh-papers")
def refresh_papers_endpoint(req: RefreshPapersRequest) -> dict:
    """Re-fetch publications from ORCID or Semantic Scholar for a confirmed ID."""
    from engine.researcher_ids import fetch_orcid_works, fetch_s2_author_papers, validate_orcid
    profile = store._get_profile(req.profile_name)

    if req.confirm:
        if req.id_type == "orcid" and not validate_orcid(req.id_value, profile.name, profile.affiliation):
            raise HTTPException(400, "ORCID does not match the subject name and affiliation")
        profile.researcher_ids[req.id_type] = req.id_value
        profile.confirmed_ids[req.id_type] = True

    if req.id_type == "orcid":
        new_sources = fetch_orcid_works(req.id_value)
    elif req.id_type == "semantic_scholar":
        new_sources = fetch_s2_author_papers(req.id_value, limit=20)
    else:
        raise HTTPException(400, f"Unsupported id_type: {req.id_type}")

    existing_urls = {s.url for s in profile.sources}
    new_sources = [s for s in new_sources if s.url not in existing_urls]
    for s in new_sources:
        s.human_verified = True
    new_sources = classify_sources(new_sources, store.llm())
    store._check_doi_sources(new_sources, profile.name, profile.affiliation or "")
    new_claims = extract_claims(profile, new_sources, store.llm())
    profile.sources.extend(new_sources)
    profile.claims.extend(new_claims)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)

    return {
        "new_source_count": len(new_sources),
        "new_claim_count": len(new_claims),
        "sources": [s.model_dump() for s in profile.sources],
        "claims": [c.model_dump() for c in profile.claims],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@router.post("/research/fetch-from-browser")
def fetch_from_browser(body: dict) -> dict:
    """Pull the current page from browser_server and add it as a source."""
    profile = store._get_profile(body["profile_name"])

    try:
        from browser_server import _dispatch, _running
        if not _running:
            raise HTTPException(503, "Browser server is not running")
        data = _dispatch("content")
    except Exception as e:
        raise HTTPException(503, f"Browser server error: {e}")

    url = data.get("url", "")
    text = data.get("text", "")
    if not url or url in ("about:blank", ""):
        raise HTTPException(400, "Browser has no page loaded yet")

    if any(s.url == url for s in profile.sources):
        raise HTTPException(400, "This source is already in your list.")

    source = fetch_url_source_with_paste(url, text)
    [source] = classify_sources([source], store.llm())
    flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    store._check_doi_sources([source], profile.name, profile.affiliation or "")

    profile.sources.append(source)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)

    return {
        "source": source.model_dump(),
        "blocked": False,
        "sent_to_browser": False,
        "new_claims": [],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@router.post("/research/suggest")
def suggest_urls(body: dict) -> dict:
    """Return a ranked queue of URL suggestions based on what the profile is missing."""
    from engine.suggester import suggest_next_urls
    profile = store._get_profile(body["profile_name"])
    suggestions = suggest_next_urls(profile, max_results=body.get("max_results", 8))
    return {"suggestions": suggestions}


