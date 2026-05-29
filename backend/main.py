"""FastAPI backend for wikimaker."""
from __future__ import annotations
import sys, os, json
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from engine.models import PersonProfile, PersonCandidate, Claim, VerificationState
from engine.identifier import find_candidates
from engine.researcher import fetch_auto_sources, fetch_url_source, fetch_url_source_with_paste, fetch_institution_sources, targeted_slot_search
from engine.classifier import classify_sources
from engine.notability import score_notability
from engine.extractor import extract_claims, find_missing_slots, SLOT_SOURCE_HINTS
from engine.relevance import flag_sources
from engine.crawler import crawl
from engine.llm import get_provider
from engine.researcher_ids import (
    extract_ids_from_sources, is_sd_article_url, is_sd_author_url,
    resolve_sd_article, find_openalex_id_for_person, fetch_openalex_works,
    extract_sd_pii, _SD_AUTHOR_RE,
)
from engine.author_check import check_doi_authors, extract_doi
from wiki.wiki_check import check_existing_page
from wiki.wikitext import render_en, render_hi

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="wikimaker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3890", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_llm = None

def llm():
    global _llm
    if _llm is None:
        _llm = get_provider()
    return _llm


# ── Request/response models ────────────────────────────────────────────────

class IdentifyRequest(BaseModel):
    name: str
    field: Optional[str] = None
    affiliation: Optional[str] = None


class ResearchRequest(BaseModel):
    name: str
    wikidata_id: Optional[str] = None
    wikipedia_url: Optional[str] = None
    photo_url: Optional[str] = None
    field: Optional[str] = None
    affiliation: Optional[str] = None
    nationality: Optional[str] = None
    birth_year: Optional[str] = None


class AddSourceRequest(BaseModel):
    profile_name: str
    url: str


class AddDocumentFact(BaseModel):
    """A fact the user typed from a document — has no web source, timeline only."""
    profile_name: str
    field: str
    text: str


class VerifyClaimRequest(BaseModel):
    claim_index: int
    action: str   # confirm | edit | skip
    edited_text: Optional[str] = None  # only for action=edit


class AddSourcePaste(BaseModel):
    """User pasted text from a blocked page, screenshot, or PDF."""
    profile_name: str
    url: str           # the real URL (for citation) — even if we couldn't fetch it
    pasted_text: str   # what the user copied from the page


class CrawlRequest(BaseModel):
    profile_name: str
    seed_urls: list[str]
    keywords: list[str] = []
    max_nodes: int = 40
    max_depth: int = 3


class TargetedSearchRequest(BaseModel):
    profile_name: str
    slot: str
    hint: Optional[str] = None


class DraftRequest(BaseModel):
    profile: PersonProfile
    generate_hindi: bool = False


# ── Session store — in-memory + disk persistence ──────────────────────────

_sessions: dict[str, PersonProfile] = {}
_wiki_statuses: dict[str, dict] = {}


def _session_path(name: str) -> Path:
    safe = name.replace(" ", "_").replace("/", "_")
    return SESSIONS_DIR / f"{safe}.json"


def _save_session(name: str) -> None:
    profile = _sessions.get(name)
    if not profile:
        return
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
        import requests as _req
        st = _req.get(f"{BROWSER_SERVER}/status", timeout=1).json()
        if not st.get("running"):
            return False
        _req.post(f"{BROWSER_SERVER}/navigate", json={"url": url}, timeout=3)
        return True
    except Exception:
        return False


def _get_profile(name: str) -> PersonProfile:
    if name not in _sessions:
        raise HTTPException(404, f"No active research session for '{name}'")
    return _sessions[name]


def _check_doi_sources(sources: list, person_name: str, affiliation: str) -> None:
    """In-place: run author check on every source whose URL contains a DOI."""
    from engine.models import Source as S
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


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.post("/identify")
def identify(req: IdentifyRequest) -> dict:
    """Quick web search preview to confirm we're researching the right person."""
    from engine.researcher import _google_cse, _duckduckgo_html
    sources = _google_cse(req.name, req.field, req.affiliation) or _duckduckgo_html(req.name, req.field, req.affiliation)
    results = [
        {"title": s.title, "url": s.url, "snippet": s.snippet, "publisher": s.publisher}
        for s in sources[:5]
    ]
    return {"results": results}


@app.post("/research/start")
def research_start(req: ResearchRequest) -> dict:
    """Initialize session, run wiki check, fetch + classify sources, score notability."""
    wiki_status = check_existing_page(req.name)

    photo_url = req.photo_url
    if not photo_url:
        from engine.identifier import fetch_wikidata_photo
        photo_url = fetch_wikidata_photo(req.name)

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
    from engine.researcher_ids import extract_ids_from_sources
    found_ids = extract_ids_from_sources(sources)
    for id_type, id_val in found_ids.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    # If affiliation is known, crawl the institution website for biographical sources
    if req.affiliation:
        institution_sources = fetch_institution_sources(req.name, req.affiliation)
        existing_urls = {s.url for s in sources}
        sources.extend(s for s in institution_sources if s.url not in existing_urls)

    sources = classify_sources(sources, llm())
    _check_doi_sources(sources, req.name, req.affiliation or "")
    flag_sources(sources, req.name, req.field or "", req.affiliation or "")
    # Drop wrong-person sources before saving — keep uncertain ones (may be right, user can judge)
    sources = [s for s in sources if s.relevance_flag != "likely_wrong"]
    profile.sources = sources
    profile.notability = score_notability(req.name, sources)
    profile.claims = extract_claims(profile, sources, llm())
    profile.missing_slots = find_missing_slots(profile, profile.claims)

    _sessions[req.name] = profile
    _wiki_statuses[req.name] = wiki_status.model_dump()
    _save_session(req.name)

    return {
        "wiki_status": wiki_status.model_dump(),
        "notability": profile.notability.model_dump(),
        "profile": profile.model_dump(),
    }


@app.post("/research/add-source")
def add_source(req: AddSourceRequest) -> dict:
    """User pastes a URL — fetch it, classify it, extract claims from it.

    Special cases:
    - ScienceDirect article URL: resolved via PII→CrossRef→OpenAlex pipeline
    - ScienceDirect author URL: Scopus ID extracted, stored in researcher_ids
    """
    profile = _get_profile(req.profile_name)
    url = req.url

    if any(s.url == url for s in profile.sources):
        raise HTTPException(400, "This source is already in your list.")

    # ── ScienceDirect article: use PII pipeline instead of fetching ───────────
    if is_sd_article_url(url):
        return _add_sd_article(profile, url)

    # ── ScienceDirect author profile: extract Scopus ID + fetch OpenAlex works ─
    if is_sd_author_url(url):
        return _add_sd_author_profile(profile, url)

    # ── Normal URL fetch ──────────────────────────────────────────────────────
    source, blocked = fetch_url_source(url, profile.name)
    [source] = classify_sources([source], llm())
    flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    _check_doi_sources([source], profile.name, profile.affiliation or "")

    # Extract researcher IDs from the new URL (e.g. user pastes an ORCID link)
    from engine.researcher_ids import extract_ids_from_sources
    new_ids = extract_ids_from_sources([source])
    for id_type, id_val in new_ids.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    profile.sources.append(source)
    # Claims are extracted on confirmation, not on add
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)

    # If blocked, push to human browser_server if it's running
    sent_to_browser = False
    if blocked:
        sent_to_browser = _push_to_browser(url)

    return {
        "source": source.model_dump(),
        "blocked": blocked,
        "sent_to_browser": sent_to_browser,
        "new_claims": [],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


def _add_sd_article(profile, url: str) -> dict:
    """Resolve a ScienceDirect article URL via PII→CrossRef→OpenAlex."""
    from engine.models import Source as Src, SourceReliability
    from engine.researcher import _extract_publisher

    resolved = resolve_sd_article(url)
    if not resolved:
        # Fall back to normal fetch
        source, blocked = fetch_url_source(url, profile.name)
        [source] = classify_sources([source], llm())
        profile.sources.append(source)
        profile.notability = score_notability(profile.name, profile.sources)
        _save_session(profile.name)
        return {"source": source.model_dump(), "blocked": blocked, "new_claims": [],
                "notability": profile.notability.model_dump(), "pipeline": None,
                "researcher_ids": profile.researcher_ids, "confirmed_ids": profile.confirmed_ids}

    doi = resolved["doi"]
    doi_url = f"https://doi.org/{doi}"

    # Add the article itself as a source (via DOI URL, already canonical)
    existing_urls = {s.url for s in profile.sources}
    new_sources: list = []
    pipeline_msg: dict = {
        "doi": doi,
        "title": resolved["title"],
        "crossref_authors": [f"{a.get('given','')} {a.get('family','')}".strip()
                              for a in resolved["crossref_authors"]],
        "openalex_author_id": None,
        "openalex_works_added": 0,
    }

    if doi_url not in existing_urls:
        article_source = Src(
            url=doi_url,
            title=resolved["title"],
            publisher=resolved["publisher"],
            reliability=SourceReliability.reliable_secondary,
            snippet=f"Published {resolved['year'] or 'unknown year'}. Authors: " +
                    ", ".join(pipeline_msg["crossref_authors"][:6]),
            date=str(resolved["year"]) if resolved["year"] else None,
            fetched_by="openalex",
            user_provided=True,
        )
        [article_source] = classify_sources([article_source], llm())
        _check_doi_sources([article_source], profile.name, profile.affiliation or "")
        new_sources.append(article_source)

    # Find person in author list → get OpenAlex author ID
    oa_author_id = find_openalex_id_for_person(profile.name, resolved["openalex_authorships"])
    if oa_author_id:
        pipeline_msg["openalex_author_id"] = oa_author_id
        profile.researcher_ids["openalex"] = oa_author_id

        # Fetch their full works list
        oa_works = fetch_openalex_works(oa_author_id, limit=30)
        for s in oa_works:
            if s.url not in existing_urls and s.url not in {ns.url for ns in new_sources}:
                new_sources.append(s)
        pipeline_msg["openalex_works_added"] = len(new_sources) - (1 if doi_url not in existing_urls else 0)

    new_sources = classify_sources(new_sources, llm()) if new_sources else []
    flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
    new_claims = extract_claims(profile, new_sources, llm()) if new_sources else []

    profile.sources.extend(new_sources)
    profile.claims.extend(new_claims)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)

    # Return the canonical article source as the "added source" for UI
    main_source = next((s for s in new_sources if s.url == doi_url), new_sources[0] if new_sources else None)
    return {
        "source": main_source.model_dump() if main_source else None,
        "blocked": False,
        "new_claims": [c.model_dump() for c in new_claims],
        "notability": profile.notability.model_dump(),
        "pipeline": pipeline_msg,
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


def _add_sd_author_profile(profile, url: str) -> dict:
    """Extract Scopus ID from ScienceDirect author URL and fetch OpenAlex works."""
    m = _SD_AUTHOR_RE.search(url)
    scopus_id = m.group(1) if m else None

    if scopus_id:
        profile.researcher_ids["scopus"] = scopus_id

    # Try to find OpenAlex author by name, then fetch works
    from engine.researcher import _extract_publisher
    from engine.models import Source as Src, SourceReliability

    # Add the author profile page as a source (may be blocked, that's ok)
    source, blocked = fetch_url_source(url, profile.name)
    if blocked:
        source.title = f"ScienceDirect author profile: {profile.name}"
        source.snippet = f"Scopus author ID: {scopus_id}" if scopus_id else "ScienceDirect author profile"

    source.user_provided = True
    [source] = classify_sources([source], llm())
    flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    profile.sources.append(source)

    new_claims: list = []
    # Fetch OpenAlex works by searching author name
    oa_works: list = []
    oa_author_id = None
    try:
        import requests as rq
        resp = rq.get(
            "https://api.openalex.org/authors",
            params={"search": profile.name, "per-page": 5},
            headers={"User-Agent": "wikimaker/0.1 (ay.yadav53@gmail.com)"},
            timeout=10,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            # Pick best match by affiliation
            affil_kw = [t.lower() for t in (profile.affiliation or "").split() if len(t) > 3]
            for r in results:
                aff_text = " ".join(
                    a.get("institution", {}).get("display_name", "")
                    for a in r.get("affiliations", [])
                ).lower()
                if any(k in aff_text for k in affil_kw):
                    oa_author_id = r["id"].split("/")[-1]
                    break
            if not oa_author_id and results:
                oa_author_id = results[0]["id"].split("/")[-1]
    except Exception:
        pass

    if oa_author_id:
        profile.researcher_ids["openalex"] = oa_author_id
        existing_urls = {s.url for s in profile.sources}
        oa_works = [s for s in fetch_openalex_works(oa_author_id, limit=30) if s.url not in existing_urls]
        oa_works = classify_sources(oa_works, llm())
        new_claims = extract_claims(profile, oa_works, llm())
        profile.sources.extend(oa_works)
        profile.claims.extend(new_claims)

    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)

    return {
        "source": source.model_dump(),
        "blocked": blocked,
        "new_claims": [c.model_dump() for c in new_claims],
        "notability": profile.notability.model_dump(),
        "pipeline": {"scopus_id": scopus_id, "openalex_author_id": oa_author_id,
                     "openalex_works_added": len(oa_works)},
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@app.post("/research/add-document-fact")
def add_document_fact(req: AddDocumentFact) -> dict:
    """User types a fact from a document — no URL, timeline-only, marked unsourced."""
    profile = _get_profile(req.profile_name)
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


@app.post("/research/verify-claim")
def verify_claim(name: str, req: VerifyClaimRequest) -> dict:
    profile = _get_profile(name)
    if req.claim_index >= len(profile.claims):
        raise HTTPException(400, "claim_index out of range")

    claim = profile.claims[req.claim_index]
    if req.action == "confirm":
        claim.verification = VerificationState.confirmed
    elif req.action == "edit" and req.edited_text:
        claim.text = req.edited_text
        claim.verification = VerificationState.edited
    elif req.action == "skip":
        claim.verification = VerificationState.skipped

    _save_session(name)
    return {"claim": claim.model_dump()}


@app.post("/research/add-source-paste")
def add_source_paste(req: AddSourcePaste) -> dict:
    """User pasted text from a blocked page (or typed from a screenshot/PDF)."""
    profile = _get_profile(req.profile_name)
    source = fetch_url_source_with_paste(req.url, req.pasted_text)
    [source] = classify_sources([source], llm())
    flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    new_claims = extract_claims(profile, [source], llm())
    profile.sources.append(source)
    profile.claims.extend(new_claims)
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)
    return {
        "source": source.model_dump(),
        "new_claims": [c.model_dump() for c in new_claims],
        "notability": profile.notability.model_dump(),
    }


@app.post("/research/crawl")
def deep_crawl(req: CrawlRequest) -> dict:
    """Start from seed URLs and crawl outward — follow links to find more sources."""
    profile = _get_profile(req.profile_name)
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
    new_sources = classify_sources(new_sources, llm())

    # Only keep sources that mention the person at least once
    relevant = [
        s for s in new_sources
        if graph.relevance_hits.get(s.url, 0) > 0
    ]

    new_claims = extract_claims(profile, relevant, llm())
    profile.sources.extend(relevant)
    profile.claims.extend(new_claims)
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)

    return {
        "nodes_crawled": len(graph.nodes),
        "relevant_sources": len(relevant),
        "new_claims": len(new_claims),
        "notability": profile.notability.model_dump(),
        "sources": [s.model_dump() for s in relevant],
    }


@app.post("/research/targeted-search")
def targeted_search_endpoint(req: TargetedSearchRequest) -> dict:
    """Search for sources likely to fill a specific Wikipedia slot."""
    profile = _get_profile(req.profile_name)
    sources = targeted_slot_search(
        person_name=profile.name,
        slot=req.slot,
        field=profile.field,
        affiliation=profile.affiliation,
        hint=req.hint,
    )
    # Deduplicate against existing sources
    existing_urls = {s.url for s in profile.sources}
    new_sources = [s for s in sources if s.url not in existing_urls]
    new_sources = classify_sources(new_sources, llm())
    flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
    new_claims = extract_claims(profile, new_sources, llm())

    profile.sources.extend(new_sources)
    profile.claims.extend(new_claims)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)

    return {
        "sources": [s.model_dump() for s in new_sources],
        "new_claims": [c.model_dump() for c in new_claims],
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump(),
    }


@app.post("/draft")
def generate_draft(req: DraftRequest) -> dict:
    profile = req.profile
    profile.wikitext_en = render_en(profile, llm())
    if req.generate_hindi:
        profile.wikitext_hi = render_hi(profile, llm())
    return {"profile": profile.model_dump()}


@app.get("/session/{name}")
def get_session(name: str) -> dict:
    return {"profile": _get_profile(name).model_dump()}


@app.post("/research/source/verify")
def verify_source(body: dict) -> dict:
    """Mark a source as human-verified. On verify, extract claims from it."""
    profile = _get_profile(body["profile_name"])
    url = body["url"]
    verified = body.get("verified", True)
    source = next((s for s in profile.sources if s.url == url), None)
    if not source:
        return {"ok": True, "new_claims": [], "missing_slots": profile.missing_slots}

    source.human_verified = verified
    new_claims: list = []

    if verified and source.snippet and source.relevance_flag != "likely_wrong":
        already_sourced = {c.source_url for c in profile.claims}
        if url not in already_sourced:
            new_claims = extract_claims(profile, [source], llm())
            profile.claims.extend(new_claims)
            profile.missing_slots = find_missing_slots(profile, profile.claims)

    _save_session(profile.name)
    return {
        "ok": True,
        "new_claims": [c.model_dump() for c in new_claims],
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@app.post("/research/source/reject")
def reject_source(body: dict) -> dict:
    """Remove a source and all claims extracted from it."""
    profile = _get_profile(body["profile_name"])
    url = body["url"]
    profile.sources = [s for s in profile.sources if s.url != url]
    removed = [c for c in profile.claims if c.source_url == url]
    profile.claims = [c for c in profile.claims if c.source_url != url]
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)
    return {
        "removed_claim_count": len(removed),
        "notability": profile.notability.model_dump(),
        "sources": [s.model_dump() for s in profile.sources],
        "claims": [c.model_dump() for c in profile.claims],
    }


@app.get("/sessions")
def list_sessions() -> dict:
    """List all saved research sessions from disk."""
    sessions = []
    for path in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = _load_session_file(path)
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


@app.delete("/sessions/{filename}")
def delete_session(filename: str) -> dict:
    """Delete a saved session file and remove from in-memory cache."""
    if "/" in filename or "\\" in filename or not filename.endswith(".json"):
        raise HTTPException(400, "Invalid filename")
    path = SESSIONS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Session file not found: {filename}")
    # Derive person name from file to evict in-memory session
    data = _load_session_file(path)
    if data:
        person_name = data.get("profile", {}).get("name")
        if person_name and person_name in _sessions:
            del _sessions[person_name]
        if person_name and person_name in _wiki_statuses:
            del _wiki_statuses[person_name]
    path.unlink()
    return {"deleted": filename}


class FindIdsRequest(BaseModel):
    profile_name: str


class RefreshPapersRequest(BaseModel):
    profile_name: str
    id_type: str   # orcid | semantic_scholar
    id_value: str
    confirm: bool = False  # if True, mark as confirmed before refreshing


@app.post("/research/find-researcher-ids")
def find_researcher_ids_endpoint(req: FindIdsRequest) -> dict:
    """Search for ORCID, Google Scholar, Scopus, ResearchGate IDs and validate ORCID."""
    from engine.researcher_ids import search_researcher_ids, validate_orcid
    profile = _get_profile(req.profile_name)
    found = search_researcher_ids(profile.name, profile.field, profile.affiliation)
    for id_type, id_val in found.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    # Auto-validate ORCID if found
    if "orcid" in profile.researcher_ids and not profile.confirmed_ids.get("orcid"):
        valid = validate_orcid(profile.researcher_ids["orcid"], profile.name, profile.affiliation)
        profile.confirmed_ids["orcid"] = valid

    _save_session(profile.name)
    return {
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@app.post("/research/refresh-papers")
def refresh_papers_endpoint(req: RefreshPapersRequest) -> dict:
    """Re-fetch publications from ORCID or Semantic Scholar for a confirmed ID."""
    from engine.researcher_ids import fetch_orcid_works, fetch_s2_author_papers
    profile = _get_profile(req.profile_name)

    if req.confirm:
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
    new_sources = classify_sources(new_sources, llm())
    _check_doi_sources(new_sources, profile.name, profile.affiliation or "")
    new_claims = extract_claims(profile, new_sources, llm())

    profile.sources.extend(new_sources)
    profile.claims.extend(new_claims)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)

    return {
        "new_source_count": len(new_sources),
        "new_claim_count": len(new_claims),
        "sources": [s.model_dump() for s in profile.sources],
        "claims": [c.model_dump() for c in profile.claims],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@app.post("/sessions/resume")
def resume_session(body: dict) -> dict:
    """Load a saved session from disk into memory and return it."""
    filename = body.get("file")
    if not filename:
        raise HTTPException(400, "file required")
    path = SESSIONS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Session file not found: {filename}")
    data = _load_session_file(path)
    if not data:
        raise HTTPException(500, "Could not read session file")

    profile = PersonProfile(**data["profile"])
    wiki_status = data.get("wiki_status", {"status": "clear", "url": None, "note": None})

    # If session has sources but no claims (was saved before LLM was available), re-extract now
    if profile.sources and not profile.claims:
        profile.claims = extract_claims(profile, profile.sources, llm())
    flag_sources(profile.sources, profile.name, profile.field or "", profile.affiliation or "")
    profile.missing_slots = find_missing_slots(profile, profile.claims)

    # Rescan source URLs for researcher IDs missed by older sessions
    found_ids = extract_ids_from_sources(profile.sources)
    for id_type, id_val in found_ids.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    _sessions[profile.name] = profile
    _wiki_statuses[profile.name] = wiki_status
    _save_session(profile.name)

    return {
        "profile": profile.model_dump(),
        "wiki_status": wiki_status,
    }


@app.post("/research/fetch-from-browser")
def fetch_from_browser(body: dict) -> dict:
    """Pull the current page from browser_server and add it as a source."""
    import requests as _req
    profile = _get_profile(body["profile_name"])

    try:
        data = _req.get(f"{BROWSER_SERVER}/content", timeout=8).json()
    except Exception as e:
        raise HTTPException(503, f"Browser server not reachable: {e}")

    url = data.get("url", "")
    text = data.get("text", "")
    if not url or url in ("about:blank", ""):
        raise HTTPException(400, "Browser has no page loaded yet")

    if any(s.url == url for s in profile.sources):
        raise HTTPException(400, "This source is already in your list.")

    source = fetch_url_source_with_paste(url, text)
    [source] = classify_sources([source], llm())
    flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    _check_doi_sources([source], profile.name, profile.affiliation or "")

    profile.sources.append(source)
    profile.notability = score_notability(profile.name, profile.sources)
    _save_session(profile.name)

    return {
        "source": source.model_dump(),
        "blocked": False,
        "sent_to_browser": False,
        "new_claims": [],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@app.post("/research/suggest")
def suggest_urls(body: dict) -> dict:
    """Return a ranked queue of URL suggestions based on what the profile is missing."""
    from engine.suggester import suggest_next_urls
    profile = _get_profile(body["profile_name"])
    suggestions = suggest_next_urls(profile, max_results=body.get("max_results", 8))
    return {"suggestions": suggestions}
