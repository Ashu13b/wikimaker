import pytest
from fastapi import HTTPException

from backend import main as backend_main
from backend import store
from engine import researcher_ids
from engine.models import PersonProfile, Source, SourceReliability


def _profile() -> PersonProfile:
    return PersonProfile(
        name="Prem Singh Yadav",
        affiliation="ICAR-Central Institute for Research on Buffaloes",
    )


def test_find_ids_removes_an_orcid_that_fails_identity_validation(monkeypatch):
    profile = _profile()
    profile.researcher_ids["orcid"] = "0000-0003-0982-9408"
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_save_session", lambda _name: None)
    monkeypatch.setattr(researcher_ids, "search_researcher_ids", lambda *_args: {})
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_args: False)

    result = backend_main.find_researcher_ids_endpoint(
        backend_main.FindIdsRequest(profile_name=profile.name)
    )

    assert "orcid" not in result["researcher_ids"]
    assert result["confirmed_ids"]["orcid"] is False


def test_refresh_rejects_an_unvalidated_orcid(monkeypatch):
    profile = _profile()
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_args: False)

    with pytest.raises(HTTPException) as exc:
        backend_main.refresh_papers_endpoint(
            backend_main.RefreshPapersRequest(
                profile_name=profile.name,
                id_type="orcid",
                id_value="0000-0003-0982-9408",
                confirm=True,
            )
        )

    assert exc.value.status_code == 400
    assert profile.researcher_ids == {}


def test_validated_new_ids_drops_wrong_person_orcid(monkeypatch):
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_a, **_k: False)

    out = researcher_ids.validated_new_ids(
        {"orcid": "0000-0003-0982-9408", "google_scholar": "namesake123"},
        "Prem Singh Yadav",
    )

    assert "orcid" not in out
    assert out["google_scholar"] == "namesake123"


def test_validated_new_ids_keeps_verified_orcid(monkeypatch):
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_a, **_k: True)

    out = researcher_ids.validated_new_ids({"orcid": "0000-0002-1825-0097"}, "Prem Singh Yadav")

    assert out == {"orcid": "0000-0002-1825-0097"}


def test_research_start_drops_orcid_from_source_url_when_validation_fails(monkeypatch, tmp_path):
    orcid_source = Source(
        url="https://orcid.org/0000-0003-0982-9408",
        title="ORCID profile of someone else",
        publisher="ORCID",
        reliability=SourceReliability.primary,
        fetched_by="google_search",
    )
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(
        "backend.routes_research.fetch_auto_sources",
        lambda *a, **k: ([orcid_source], None),
    )
    monkeypatch.setattr(
        "backend.routes_research._enrich_and_flag_sources",
        lambda sources, *a: sources,
    )

    class _Clear:
        def model_dump(self):
            return {"status": "clear", "url": None, "note": None}

    monkeypatch.setattr("backend.routes_research.check_existing_page", lambda _t: _Clear())
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_a, **_k: False)

    result = backend_main.research_start(
        backend_main.ResearchRequest(name="Fresh Person")
    )

    assert result["resumed"] is False
    assert "orcid" not in result["profile"]["researcher_ids"]


def test_research_start_keeps_orcid_when_validation_passes(monkeypatch, tmp_path):
    orcid_source = Source(
        url="https://orcid.org/0000-0002-1825-0097",
        title="ORCID profile",
        publisher="ORCID",
        reliability=SourceReliability.primary,
        fetched_by="google_search",
    )
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(
        "backend.routes_research.fetch_auto_sources",
        lambda *a, **k: ([orcid_source], None),
    )
    monkeypatch.setattr(
        "backend.routes_research._enrich_and_flag_sources",
        lambda sources, *a: sources,
    )

    class _Clear:
        def model_dump(self):
            return {"status": "clear", "url": None, "note": None}

    monkeypatch.setattr("backend.routes_research.check_existing_page", lambda _t: _Clear())
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_a, **_k: True)

    result = backend_main.research_start(
        backend_main.ResearchRequest(name="Fresh Person 2")
    )

    assert result["profile"]["researcher_ids"]["orcid"] == "0000-0002-1825-0097"


def test_validate_s2_author_accepts_matching_profile(monkeypatch):
    class _Resp:
        status_code = 200
        def json(self):
            return {"name": "Vishwa Mohan Katoch"}
    monkeypatch.setattr(researcher_ids.requests, "get", lambda *a, **k: _Resp())

    assert researcher_ids.validate_s2_author("2147684", "Vishwa Mohan Katoch") is True


def test_validate_s2_author_rejects_namesake_and_missing(monkeypatch):
    class _Namesake:
        status_code = 200
        def json(self):
            return {"name": "Ramesh Katoch"}
    class _Missing:
        status_code = 404
        def json(self):
            return {}
    monkeypatch.setattr(researcher_ids.requests, "get", lambda *a, **k: _Namesake())
    assert researcher_ids.validate_s2_author("1", "Vishwa Mohan Katoch") is False
    monkeypatch.setattr(researcher_ids.requests, "get", lambda *a, **k: _Missing())
    assert researcher_ids.validate_s2_author("1", "Vishwa Mohan Katoch") is False


def test_validated_new_ids_drops_wrong_semantic_scholar_id(monkeypatch):
    monkeypatch.setattr(researcher_ids, "validate_s2_author", lambda *_a, **_k: False)

    out = researcher_ids.validated_new_ids(
        {"semantic_scholar": "2147684"}, "Vishwa Mohan Katoch"
    )

    assert out == {}
