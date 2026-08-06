"""ScienceDirect -> CrossRef -> OpenAlex pipelines used by the add-source routes."""
from __future__ import annotations

from . import store
from engine.models import Source as Src, SourceReliability
from engine.researcher import fetch_url_source
from engine.classifier import classify_sources
from engine.notability import score_notability
from engine.extractor import extract_claims, find_missing_slots
from engine.relevance import flag_sources
from engine.researcher_ids import (
    resolve_sd_article, find_openalex_id_for_person, fetch_openalex_works, _SD_AUTHOR_RE,
)

def _add_sd_article(profile, url: str) -> dict:
    """Resolve a ScienceDirect article URL via PII→CrossRef→OpenAlex."""
    resolved = resolve_sd_article(url)
    if not resolved:
        # Fall back to normal fetch
        source, blocked = fetch_url_source(url, profile.name)
        [source] = classify_sources([source], store.llm())
        profile.sources.append(source)
        profile.notability = score_notability(profile.name, profile.sources)
        store._save_session(profile.name)
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
            human_verified=True,
        )
        [article_source] = classify_sources([article_source], store.llm())
        store._check_doi_sources([article_source], profile.name, profile.affiliation or "")
        new_sources.append(article_source)

    # Find person in author list → get OpenAlex author ID
    oa_author_id = find_openalex_id_for_person(profile.name, resolved["openalex_authorships"])
    if oa_author_id:
        pipeline_msg["openalex_author_id"] = oa_author_id
        profile.researcher_ids["openalex"] = oa_author_id

        # Fetch their full works list
        oa_works = fetch_openalex_works(oa_author_id, limit=30)
        for s in oa_works:
            s.human_verified = True
            if s.url not in existing_urls and s.url not in {ns.url for ns in new_sources}:
                new_sources.append(s)
        pipeline_msg["openalex_works_added"] = len(new_sources) - (1 if doi_url not in existing_urls else 0)

    new_sources = classify_sources(new_sources, store.llm()) if new_sources else []
    flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
    new_claims = extract_claims(profile, new_sources, store.llm()) if new_sources else []

    profile.sources.extend(new_sources)
    profile.claims.extend(new_claims)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)

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

    # Add the author profile page as a source (may be blocked, that's ok)
    source, blocked = fetch_url_source(url, profile.name)
    if blocked:
        source.title = f"ScienceDirect author profile: {profile.name}"
        source.snippet = f"Scopus author ID: {scopus_id}" if scopus_id else "ScienceDirect author profile"

    source.user_provided = True
    source.human_verified = True
    [source] = classify_sources([source], store.llm())
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
        for s in oa_works:
            s.human_verified = True
        oa_works = classify_sources(oa_works, store.llm())
        new_claims = extract_claims(profile, oa_works, store.llm())
        profile.sources.extend(oa_works)
        profile.claims.extend(new_claims)

    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources)
    store._save_session(profile.name)

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


