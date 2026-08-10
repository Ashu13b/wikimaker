import pytest
from fastapi import HTTPException

from backend import main as backend_main
from backend import store
from engine.models import PersonProfile, Source, SourceReliability, Claim, VerificationState
from wiki.article_compare import build_article_proposal, claim_coverage, title_from_url


def _profile() -> PersonProfile:
    src = Source(
        url="https://news.example.test/report", title="Report", publisher="Example News",
        reliability=SourceReliability.reliable_secondary, human_verified=True,
    )
    return PersonProfile(
        name="Example Person",
        sources=[src],
        claims=[
            Claim(
                field="award",
                text="Won the Nanaji Deshmukh award for buffalo cloning",
                source_url=src.url,
                verification=VerificationState.confirmed,
            ),
            Claim(
                field="position",
                text="Served as director of a remote mountain observatory",
                source_url=src.url,
                verification=VerificationState.confirmed,
            ),
        ],
    )


def test_title_from_url():
    assert title_from_url("https://en.wikipedia.org/wiki/Prem_Singh_Yadav") == "Prem Singh Yadav"
    assert title_from_url("https://en.wikipedia.org/wiki/Prem_Singh_Yadav#Awards") == "Prem Singh Yadav"


def test_claim_coverage_flags_absent_fact():
    covered = claim_coverage(
        _profile().claims[0],
        "Yadav won the Nanaji Deshmukh award for buffalo cloning at the institute.",
    )
    missing = claim_coverage(
        _profile().claims[1],
        "Yadav won the Nanaji Deshmukh award for buffalo cloning at the institute.",
    )
    assert covered.covered is True
    assert missing.covered is False


def test_temporal_year_absent_from_article_weakens_coverage():
    profile = _profile()
    profile.claims[0].date_context = "2019"
    covered = claim_coverage(profile.claims[0], "Yadav won the Nanaji Deshmukh award for buffalo cloning.")
    assert covered.covered is False


def test_build_proposal_splits_covered_and_additions():
    article_text = "Yadav won the Nanaji Deshmukh award for buffalo cloning at the institute."
    proposal = build_article_proposal(
        _profile(), "Example Person", "https://en.wikipedia.org/wiki/Example_Person", article_text
    )
    assert proposal.covered_count == 1
    assert proposal.missing_count == 1
    assert next(c for c in proposal.coverage if c.covered).field == "award"
    assert next(c for c in proposal.coverage if not c.covered).field == "position"


def test_article_proposal_route_requires_exists_status(tmp_path, monkeypatch):
    profile = _profile()
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear", "url": None, "note": None}})

    with pytest.raises(HTTPException):
        backend_main.article_proposal({"profile_name": profile.name})


def test_article_proposal_route_returns_proposal(tmp_path, monkeypatch):
    profile = _profile()
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(
        store, "_wiki_statuses",
        {profile.name: {"status": "exists", "url": "https://en.wikipedia.org/wiki/Example_Person", "note": None}},
    )

    import wiki.article_compare as ac
    monkeypatch.setattr(ac, "fetch_article_text", lambda title: "Yadav won the Nanaji Deshmukh award for buffalo cloning.")

    result = backend_main.article_proposal({"profile_name": profile.name})
    assert result["proposal"]["covered_count"] == 1
    assert result["proposal"]["missing_count"] == 1
