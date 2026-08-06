import pytest
from fastapi import HTTPException

from backend import main as backend_main
from backend import store
from engine import researcher_ids
from engine.models import PersonProfile


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
