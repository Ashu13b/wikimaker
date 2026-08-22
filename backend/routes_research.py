"""Research, source, and claim routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from . import store

from . import pipelines
from .schemas import (
    IdentifyRequest, ResearchRequest, AddSourceRequest, AddDocumentFact,
    AddSourcedClaimRequest, VerifyClaimRequest, BatchVerifyClaimsRequest, AddSourcePaste, CrawlRequest,
    TargetedSearchRequest, FindIdsRequest, RefreshPapersRequest, AssessSourceRequest,
)

from engine.models import PersonProfile, Claim, VerificationState, SourceReliability
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
    extract_ids_from_sources,
    is_sd_article_url,
    is_sd_author_url,
    validated_new_ids,
)
from engine.provenance import normalize_url
from wiki.wiki_check import check_existing_page

research_router = APIRouter()

@research_router.post("/identify")
def identify(req: IdentifyRequest) -> dict:
    """Preview identity clues to confirm the right person.

    Wikipedia/Wikidata candidates carry stable identifiers (wikidata_id,
    wikipedia_url) the user can confirm into the session; generic web snippets
    are corroborating clues only.
    """
    hints = " ".join(x for x in (req.field, req.affiliation) if x)
    identity = []
    try:
        from engine.identifier import find_candidates
        identity = find_candidates(req.name, hints)
    except Exception:
        identity = []

    web = []
    try:
        from engine.researcher import _google_cse, _duckduckgo_html
        web = _google_cse(req.name, req.field, req.affiliation) or _duckduckgo_html(req.name, req.field, req.affiliation) or []
    except Exception:
        web = []

    results = [
        {
            "kind": "identity",
            "title": c.name,
            "url": c.wikipedia_url or f"https://www.wikidata.org/wiki/{c.wikidata_id}",
            "snippet": c.bio_snippet or "",
            "publisher": "Wikipedia/Wikidata",
            "wikidata_id": c.wikidata_id,
            "wikipedia_url": c.wikipedia_url,
            "photo_url": c.photo_url,
            "birth_year": c.birth_year,
            "nationality": c.nationality,
            "field": c.field,
            "affiliation": c.affiliation,
        }
        for c in identity
    ]
    results += [
        {"kind": "web", "title": s.title, "url": s.url, "snippet": s.snippet, "publisher": s.publisher}
        for s in web[:5]
    ]

    # Show the Wikimedia routing outcome up front so the user knows before
    # starting whether this will be new-article or existing-article/draft mode.
    # Prefer the confirmed identity match's article title when one is offered.
    wiki_status = None
    try:
        from wiki.wiki_check import check_existing_page, check_title_for
        title = check_title_for(req.name, identity[0].wikipedia_url) if identity and identity[0].wikipedia_url else req.name
        wiki_status = check_existing_page(title).model_dump()
    except Exception:
        wiki_status = None

    return {"results": results, "wiki_status": wiki_status}


def _find_resumable_session(req: ResearchRequest) -> PersonProfile | None:
    """Check in-memory store and disk for an existing session with matching identity."""
    existing = next(
        (p for p in store._sessions.values()
         if store._identity_matches({"name": p.name, "wikidata_id": p.wikidata_id},
                                    req.name, req.wikidata_id)),
        None)
    if existing is None:
        hit = store._find_session_on_disk(
            lambda d: store._identity_matches(d, req.name, req.wikidata_id))
        if hit is not None:
            data, path = hit
            profile = PersonProfile(**data["profile"])
            existing = store._activate_session(
                profile, data.get("wiki_status", {"status": "clear", "url": None, "note": None}))
            sid = store._ensure_session_id(existing)
            store._save_session(sid)
            id_path = store._session_path(sid)
            if path != id_path and id_path.exists():
                path.unlink()  # drop the legacy name-based file now migrated
    return existing


def _enrich_and_flag_sources(sources: list, name: str, field: str = "", affiliation: str = "") -> list:
    """Enrich sources with classification, DOI verification, and relevance flags."""
    if not sources:
        return sources
    classified = classify_sources(sources, store.llm())
    store._check_doi_sources(classified, name, affiliation or "")
    flag_sources(classified, name, field or "", affiliation or "")
    return classified


def _populate_initial_sources(profile: PersonProfile, req: ResearchRequest) -> None:
    """Fetch, classify, and filter initial sources for a newly created session."""
    sources, s2_author_id = fetch_auto_sources(req.name, req.field, req.affiliation)
    if s2_author_id:
        profile.researcher_ids["semantic_scholar"] = s2_author_id

    found_ids = extract_ids_from_sources(sources)
    new_ids = {t: v for t, v in found_ids.items() if t not in profile.researcher_ids}
    for id_type, id_val in validated_new_ids(new_ids, req.name, req.affiliation).items():
        profile.researcher_ids[id_type] = id_val

    if req.affiliation:
        institution_sources = fetch_institution_sources(req.name, req.affiliation)
        existing_urls = {s.url for s in sources}
        sources.extend(s for s in institution_sources if s.url not in existing_urls)

    sources = _enrich_and_flag_sources(sources, req.name, req.field or "", req.affiliation or "")
    profile.sources = [s for s in sources if s.relevance_flag != "likely_wrong"]
    profile.claims = []
    profile.notability = score_notability(req.name, [])
    profile.missing_slots = find_missing_slots(profile, [])


@research_router.post("/research/start")
def research_start(req: ResearchRequest) -> dict:
    """Initialize session, run wiki check, fetch + classify sources, score notability.

    Same-identity collision policy: if a session with the same display name AND a
    matching identity hint already exists (wikidata_id equal, or neither has one),
    it is resumed instead of creating a duplicate. Same name with a different
    identity hint creates a distinct session — same-named people never collide.
    """
    existing = _find_resumable_session(req)
    if existing is not None:
        sid = store._ensure_session_id(existing)
        return {
            "wiki_status": store._wiki_statuses.get(sid),
            "notability": existing.notability.model_dump() if existing.notability else None,
            "profile": existing.model_dump(),
            "resumed": True,
        }

    from wiki.wiki_check import check_title_for
    wiki_status = check_existing_page(check_title_for(req.name, req.wikipedia_url))

    photo_url = req.photo_url
    if not photo_url and req.wikidata_id:
        from engine.identifier import fetch_wikidata_photo_by_id
        photo_url = fetch_wikidata_photo_by_id(req.wikidata_id)

    profile = PersonProfile(
        name=req.name,
        session_id=store._new_session_id(req.name),
        wikidata_id=req.wikidata_id,
        wikipedia_url=req.wikipedia_url,
        photo_url=photo_url,
        field=req.field,
        affiliation=req.affiliation,
        nationality=req.nationality,
        birth_date=req.birth_year,
    )
    _populate_initial_sources(profile, req)

    sid = store._ensure_session_id(profile)
    with store._lock:
        store._sessions[sid] = profile
        store._wiki_statuses[sid] = wiki_status.model_dump()
    store._save_session(sid)

    return {
        "wiki_status": wiki_status.model_dump(),
        "notability": profile.notability.model_dump() if profile.notability else None,
        "profile": profile.model_dump(),
        "resumed": False,
    }

@research_router.post("/research/add-source")
def add_source(req: AddSourceRequest) -> dict:
    """User pastes a URL — fetch it, classify it, extract claims from it.

    Special cases:
    - ScienceDirect article URL: resolved via PII→CrossRef→OpenAlex pipeline
    - ScienceDirect author URL: Scopus ID extracted, stored in researcher_ids
    """
    profile = store._get_profile(req.profile_name)
    url = req.url

    if any(normalize_url(s.url) == normalize_url(url) for s in profile.sources):
        raise HTTPException(400, "This source is already in your list.")

    # ── ScienceDirect article: use PII pipeline instead of fetching ───────────
    if is_sd_article_url(url):
        return pipelines._add_sd_article(profile, url)

    # ── ScienceDirect author profile: extract Scopus ID + fetch OpenAlex works ─
    if is_sd_author_url(url):
        return pipelines._add_sd_author_profile(profile, url)

    # ── Normal URL fetch ──────────────────────────────────────────────────────
    source, blocked = fetch_url_source(url, profile.name)
    [source] = _enrich_and_flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    source.liveness = "blocked" if blocked else "alive"

    # Extract researcher IDs from the new URL (e.g. user pastes an ORCID link)
    new_ids = {
        t: v for t, v in extract_ids_from_sources([source]).items()
        if t not in profile.researcher_ids
    }
    for id_type, id_val in validated_new_ids(new_ids, profile.name, profile.affiliation).items():
        profile.researcher_ids[id_type] = id_val

    if url in profile.rejected_sources:
        profile.rejected_sources.remove(url)
    if url in profile.skipped_sources:
        profile.skipped_sources.remove(url)

    profile.sources.append(source)
    # Claims are extracted on confirmation, not on add
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
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


@research_router.post("/research/add-document-fact")
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


@research_router.post("/research/add-sourced-claim")
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
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile.name)
    return {
        "claim": claim.model_dump(),
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@research_router.post("/research/verify-claim")
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
        source = next((source for source in profile.sources if source.url == claim.source_url), None)
        if source is None or not source.human_verified:
            raise HTTPException(400, "Draft claims require a human-verified source")
        if claim.verification in {VerificationState.unverified, VerificationState.skipped}:
            claim.verification = VerificationState.confirmed
        claim.draft_approved = True
        claim.draft_text = req.edited_text or claim.text
    elif req.action == "edit_draft_text" and req.edited_text:
        source = next((source for source in profile.sources if source.url == claim.source_url), None)
        if source is None or not source.human_verified:
            raise HTTPException(400, "Draft claims require a human-verified source")
        if claim.verification in {VerificationState.unverified, VerificationState.skipped}:
            claim.verification = VerificationState.confirmed
        claim.draft_text = req.edited_text
        claim.draft_approved = True
    elif req.action == "remove_draft":
        claim.draft_approved = False
        claim.draft_text = None
    else:
        raise HTTPException(400, f"Unsupported claim action: {req.action}")

    store._save_session(name)
    return {"claim": claim.model_dump()}


@research_router.post("/research/batch-verify-claims")
def batch_verify_claims(name: str, req: BatchVerifyClaimsRequest) -> dict:
    """Batch approve, confirm, or skip unreviewed claims."""
    profile = store._get_profile(name)
    sources_by_url = {normalize_url(s.url): s for s in profile.sources}
    count = 0

    if req.action == "approve_all_usable":
        for claim in profile.claims:
            if claim.verification == VerificationState.unverified:
                source = sources_by_url.get(normalize_url(claim.source_url)) if claim.source_url else None
                if (
                    source
                    and source.human_verified
                    and source.reliability != SourceReliability.unreliable
                    and source.relevance_flag != "likely_wrong"
                    and not (source.liveness == "dead" and not source.archive_url)
                ):
                    claim.verification = VerificationState.confirmed
                    claim.draft_approved = True
                    claim.draft_text = claim.text
                    count += 1
    elif req.action == "confirm_all":
        for claim in profile.claims:
            if claim.verification == VerificationState.unverified:
                claim.verification = VerificationState.confirmed
                count += 1
    elif req.action == "skip_unverified":
        for claim in profile.claims:
            if claim.verification == VerificationState.unverified:
                claim.verification = VerificationState.skipped
                claim.draft_approved = False
                claim.draft_text = None
                count += 1
    else:
        raise HTTPException(400, f"Unsupported batch action: {req.action}")

    store._save_session(name)
    return {"profile": profile.model_dump(), "updated_count": count}


@research_router.post("/research/add-source-paste")
def add_source_paste(req: AddSourcePaste) -> dict:
    """User pasted text from a blocked page (or typed from a screenshot/PDF)."""
    profile = store._get_profile(req.profile_name)
    source = fetch_url_source_with_paste(req.url, req.pasted_text)
    [source] = _enrich_and_flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    source.human_verified = True
    new_claims = extract_claims(profile, [source], store.llm())
    profile.sources.append(source)
    profile.claims.extend(new_claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile.name)
    return {
        "source": source.model_dump(),
        "new_claims": [c.model_dump() for c in new_claims],
        "notability": profile.notability.model_dump(),
    }


@research_router.post("/research/crawl")
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
    existing_urls = {normalize_url(s.url) for s in profile.sources}
    rejected_urls = {normalize_url(u) for u in (getattr(profile, "rejected_sources", []) or [])}
    skipped_urls = {normalize_url(u) for u in (getattr(profile, "skipped_sources", []) or [])}
    excluded = existing_urls | rejected_urls | skipped_urls

    relevant = [
        s for s in new_sources
        if graph.relevance_hits.get(s.url, 0) > 0 and normalize_url(s.url) not in excluded
    ]

    new_claims = []
    profile.sources.extend(relevant)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile.name)

    return {
        "nodes_crawled": len(graph.nodes),
        "relevant_sources": len(relevant),
        "new_claims": len(new_claims),
        "notability": profile.notability.model_dump(),
        "sources": [s.model_dump() for s in relevant],
    }


@research_router.post("/research/targeted-search")
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
    existing_urls = {normalize_url(s.url) for s in profile.sources}
    rejected_urls = {normalize_url(u) for u in (getattr(profile, "rejected_sources", []) or [])}
    skipped_urls = {normalize_url(u) for u in (getattr(profile, "skipped_sources", []) or [])}
    excluded = existing_urls | rejected_urls | skipped_urls

    new_sources = [s for s in sources if normalize_url(s.url) not in excluded]
    new_sources = _enrich_and_flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
    # Auto-added search results must be citable: never flood the session with
    # self-published or unreliable noise (LinkedIn dir pages, personal trainers, etc.)
    new_sources = [
        s for s in new_sources
        if s.reliability.value not in ("self_published", "unreliable")
        and s.relevance_flag == "relevant"
    ]
    new_claims = []
    profile.sources.extend(new_sources)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile.name)

    return {
        "sources": [s.model_dump() for s in new_sources],
        "new_claims": [c.model_dump() for c in new_claims],
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump(),
    }


@research_router.post("/research/auto-enrich")
def auto_enrich_endpoint(body: dict) -> dict:
    """Autonomous discovery loop — inspects missing slots and recursively iterates search queries."""
    profile_name = body["profile_name"]
    profile = store._get_profile(profile_name)
    missing = profile.missing_slots or find_missing_slots(profile, profile.claims)

    existing_urls = {normalize_url(s.url) for s in profile.sources}
    rejected_urls = {normalize_url(u) for u in (getattr(profile, "rejected_sources", []) or [])}
    skipped_urls = {normalize_url(u) for u in (getattr(profile, "skipped_sources", []) or [])}
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
        new_sources = [s for s in candidate_sources if normalize_url(s.url) not in excluded][: max_sources - len(added_sources)]
        if new_sources:
            new_sources = _enrich_and_flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
            new_sources = [
                s for s in new_sources
                if s.reliability.value not in ("self_published", "unreliable")
            ]
            new_claims = extract_claims(profile, new_sources, store.llm())

            profile.sources.extend(new_sources)
            profile.claims.extend(new_claims)
            excluded.update(normalize_url(s.url) for s in new_sources)
            added_sources.extend(new_sources)
            added_claims.extend(new_claims)

    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile.name)

    return {
        "ok": True,
        "added_source_count": len(added_sources),
        "added_claim_count": len(added_claims),
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump(),
    }


@research_router.post("/research/article-proposal")
def article_proposal(body: dict) -> dict:
    """Existing-article mode: compare confirmed claims against the live article
    and emit a structured edit proposal (covered vs candidate additions)."""
    from wiki.article_compare import build_article_proposal, fetch_article_text, title_from_url

    profile = store._get_profile(body["profile_name"])
    status = store._wiki_statuses.get(profile.name, {})
    if status.get("status") != "exists":
        raise HTTPException(400, "Article comparison is only available when an article already exists.")
    url = status.get("url")
    if not url:
        raise HTTPException(400, "No article URL recorded for this session.")

    title = title_from_url(url)
    try:
        article_text = fetch_article_text(title)
    except Exception as exc:
        raise HTTPException(502, f"Could not fetch the live article: {exc}")

    proposal = build_article_proposal(profile, title, url, article_text)
    return {"proposal": proposal.model_dump()}

@research_router.get("/session/{name}")
def get_session(name: str) -> dict:
    return {"profile": store._get_profile(name).model_dump()}


@research_router.post("/research/source/verify")
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

    if verified and source.relevance_flag == "likely_wrong":
        source.extraction_status = "likely_wrong"
        source.extraction_note = "Source flagged as likely a different person. No claims extracted."
    elif verified:
        existing_for_url = [c for c in profile.claims if c.source_url and normalize_url(c.source_url) == norm_target]
        if not existing_for_url:
            from engine.llm import StubProvider, NullProvider, LocalProvider
            llm_inst = store.llm()
            extracted = extract_claims(profile, [source], llm_inst)
            if extracted:
                profile.claims.extend(extracted)
                profile.missing_slots = find_missing_slots(profile, profile.claims)
                new_claims = extracted
                source.extraction_status = "extracted"
                source.extraction_note = f"{len(extracted)} claims extracted from this source."
            else:
                if isinstance(llm_inst, (StubProvider, NullProvider, LocalProvider)):
                    source.extraction_status = "stub_mode"
                    source.extraction_note = "LLM in rule/stub mode — to prevent fabrication, claims are not auto-extracted. Use '+ Add Sourced Claim' to add facts from this source."
                elif not source.snippet and (not source.title or source.title == source.url):
                    source.extraction_status = "thin_content"
                    source.extraction_note = "Page content was too short or lacked verifiable biographical statements."
                else:
                    source.extraction_status = "redundant"
                    source.extraction_note = "No novel claims found. The facts in this source are already backed by other verified sources in your session."
        else:
            new_claims = existing_for_url
            source.extraction_status = "extracted"
            source.extraction_note = f"Source verified ({len(existing_for_url)} claims in session)."

    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile.name)
    return {
        "ok": True,
        "source": source.model_dump(),
        "new_claims": [c.model_dump() for c in new_claims],
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@research_router.post("/research/source/reject")
def reject_source(body: dict) -> dict:
    """Remove a source and all claims extracted from it."""
    profile = store._get_profile(body["profile_name"])
    url = body["url"]
    profile.sources = [s for s in profile.sources if s.url != url]
    removed = [c for c in profile.claims if c.source_url == url]
    profile.claims = [c for c in profile.claims if c.source_url != url]
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile.name)
    return {
        "removed_claim_count": len(removed),
        "notability": profile.notability.model_dump(),
        "sources": [s.model_dump() for s in profile.sources],
        "claims": [c.model_dump() for c in profile.claims],
    }


@research_router.post("/research/skip-suggestion")
def skip_suggestion(body: dict) -> dict:
    """Record a suggestion as skipped so discovery stops re-offering it."""
    profile = store._get_profile(body["profile_name"])
    url = body["url"]
    if url not in profile.skipped_sources:
        profile.skipped_sources.append(url)
    store._save_session(profile.name)
    return {"ok": True}


@research_router.post("/research/find-researcher-ids")
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


@research_router.post("/research/refresh-papers")
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
    new_sources = _enrich_and_flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
    new_claims = extract_claims(profile, new_sources, store.llm())
    profile.sources.extend(new_sources)
    profile.claims.extend(new_claims)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
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


@research_router.post("/research/fetch-from-browser")
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
    [source] = _enrich_and_flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")

    profile.sources.append(source)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
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


@research_router.post("/research/fetch-blocked")
def fetch_blocked(body: dict) -> dict:
    """Auto-fetch blocked sources through the remote browser.

    Walks sources whose liveness is 'blocked', navigating the companion browser
    to each and capturing the rendered page. Stops at the first bot wall so the
    human can solve it in the companion browser, then resume. Playwright does
    the navigation and capture; a genuine CAPTCHA is the only thing that pauses.
    """
    profile = store._get_profile(body["profile_name"])
    try:
        from browser_server import _dispatch, _running, looks_like_wall
        if not _running:
            raise HTTPException(503, "Remote browser is not running — open the companion browser first.")
    except ImportError:
        raise HTTPException(503, "Remote browser is not available")

    targets = [s for s in profile.sources if s.liveness == "blocked"]
    fetched, walls = [], []
    for source in targets:
        _dispatch("navigate", url=source.url)
        data = _dispatch("content")
        text = (data.get("text") or "").strip()
        if len(text) < 200 or looks_like_wall(text):
            walls.append(source.url)
            break
        source.snippet = text[:400]
        source.liveness = "alive"
        source.fetched_by = "browser"
        [source] = _enrich_and_flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
        fetched.append(source.url)

    store._save_session(profile.name)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    return {
        "fetched": fetched,
        "walls": walls,
        "profile": profile.model_dump(),
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@research_router.post("/research/suggest")
def suggest_urls(body: dict) -> dict:
    """Return a ranked queue of URL suggestions based on what the profile is missing."""
    from engine.suggester import suggest_next_urls
    from engine.models import UrlSuggestion
    profile = store._get_profile(body["profile_name"])
    suggestions = suggest_next_urls(profile, max_results=body.get("max_results", 8))
    validated = [UrlSuggestion(**s).model_dump() for s in suggestions]
    return {"suggestions": validated}



@research_router.post("/research/source/assess")
def assess_source(req: AssessSourceRequest) -> dict:
    """Persist coverage depth, editorial origin, and durable research notes.

    Assessment affects the informational notability signal, never whether a
    confirmed claim remains available in the research dossier.
    """
    profile = store._get_profile(req.profile_name)
    source = next((item for item in profile.sources if item.url == req.url), None)
    if source is None:
        raise HTTPException(404, "Source not found in this session")
    if req.coverage_depth == "significant" and not source.human_verified:
        raise HTTPException(400, "Verify the source before marking significant coverage")

    source.coverage_depth = req.coverage_depth
    source.editorial_origin = (req.editorial_origin or "").strip() or None
    source.research_notes = req.research_notes.strip()
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile.name)
    return {
        "source": source.model_dump(),
        "notability": profile.notability.model_dump() if profile.notability else None,
    }

