import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend import main as backend_main
from backend import store
from engine.models import Claim, PersonProfile, Source, SourceReliability, VerificationState
from wiki.draft import audit_profile, render_draft


def _source(url: str, *, independent: bool = True) -> Source:
    return Source(
        url=url,
        title="Published profile of Example Person",
        publisher="Example News",
        reliability=SourceReliability.reliable_secondary if independent else SourceReliability.primary,
        human_verified=True,
        is_independent=independent,
        provenance_category="independent_secondary" if independent else "institutional_bio",
        relevance_flag="relevant",
    )


def _ready_profile() -> PersonProfile:
    profile_source = _source("https://example.test/profile")
    career_source = _source("https://institute.example.test/staff", independent=False)
    news_source = _source("https://news.example.test/report")
    return PersonProfile(
        name="Example Person",
        full_name="Dr. Example Person",
        nationality="Indian",
        field="Animal biotechnology",
        affiliation="Example Institute",
        sources=[profile_source, career_source, news_source],
        claims=[
            Claim(
                field="field",
                text="Animal biotechnology and reproductive physiology",
                source_url=profile_source.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                field="position",
                text="Principal Scientist at Example Institute",
                source_url=career_source.url,
                verification=VerificationState.edited,
                draft_approved=True,
            ),
            Claim(
                field="known_for",
                text="Led research that developed an independently reported cloning method",
                source_url=profile_source.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                field="known_for",
                text="Reported a nationally covered scientific milestone in the press",
                source_url=news_source.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
        ],
    )


def test_audit_excludes_cv_animal_birth_and_unverified_sources():
    profile = _ready_profile()
    cv = _source("file:///tmp/private-cv.pdf", independent=False)
    animal = _source("https://example.test/calf")
    unchecked = _source("https://example.test/unchecked")
    unchecked.human_verified = False
    profile.sources.extend([cv, animal, unchecked])
    profile.claims.extend([
        Claim(
            field="birth_date",
            text="Born on 10 April 1963",
            source_url=cv.url,
            verification=VerificationState.confirmed,
            draft_approved=True,
        ),
        Claim(
            field="birth_date",
            text="4 kg calf born through normal delivery in 2015",
            source_url=animal.url,
            verification=VerificationState.confirmed,
            draft_approved=True,
        ),
        Claim(
            field="award",
            text="Received an example scientific award",
            source_url=unchecked.url,
            verification=VerificationState.confirmed,
            draft_approved=True,
        ),
    ])

    audit = audit_profile(profile)
    exclusions = {issue.code: issue.count for issue in audit.exclusions}

    assert audit.ready
    assert exclusions["source_not_publicly_citable"] == 1
    assert exclusions["claim_appears_to_describe_animal"] == 1
    assert exclusions["source_not_human_verified"] == 1


def test_audit_blocks_profiles_without_explicit_draft_approval():
    profile = _ready_profile()
    for claim in profile.claims:
        claim.draft_approved = False

    audit = audit_profile(profile)

    assert not audit.ready
    assert audit.eligible_claim_count == 0
    assert any(issue.code == "no_eligible_claims" for issue in audit.blockers)


def test_audit_blocks_drafts_without_independent_secondary_coverage():
    profile = _ready_profile()
    for claim in profile.claims:
        claim.source_url = "https://institute.example.test/staff"
    profile.sources = [_source("https://institute.example.test/staff", independent=False)]

    audit = audit_profile(profile)

    assert not audit.ready
    assert any(issue.code == "insufficient_independent_coverage" for issue in audit.blockers)


def test_renderer_cites_every_included_claim_and_never_fills_biography_gaps():
    profile = _ready_profile()
    wikitext = render_draft(profile)

    assert "'''Example Person''' is an Indian scientist" in wikitext
    assert all("<ref" in line for line in wikitext.splitlines() if line.startswith("* "))
    assert "{{citation needed}}" not in wikitext
    assert "joined the Indian Council of Agricultural Research" not in wikitext
    assert "file:///" not in wikitext


def test_dr_yadav_saved_session_produces_policy_filtered_draft():
    session_path = Path(__file__).parent / "fixtures" / "Prem_Singh_Yadav.json"
    profile = PersonProfile(**json.loads(session_path.read_text())["profile"])

    audit = audit_profile(profile)
    wikitext = render_draft(profile, audit)

    assert audit.ready
    assert audit.eligible_claim_count >= 28
    assert audit.excluded_claim_count >= 95
    assert audit.independent_source_count >= 2
    assert "'''Prem Singh Yadav'''" in wikitext
    assert wikitext.count("{{cite web") >= 5
    assert "4 kg born through normal delivery" not in wikitext
    assert "file:///" not in wikitext
    assert "joined the Indian Council of Agricultural Research (ICAR) as a scientist in 1993" not in wikitext
    assert all("<ref" in line for line in wikitext.splitlines() if line.startswith("* "))
    assert wikitext.index("joining date of 12 April 1993") < wikitext.index("In 2018, The Tribune")
    assert wikitext.index("In 2018, The Tribune") < wikitext.index("In 2022, a PTI report")
    assert wikitext.index("In 2022, a PTI report") < wikitext.index("2024 annual report")
    assert wikitext.index("2024 annual report") < wikitext.index("retired as an ICAR-CIRB principal scientist in 2025")
    assert "DAAD Research support in 2010" in wikitext
    assert "research stay at Farm Animal Genetics, Germany" in wikitext
    assert "National Academy of Dairy Science" not in wikitext
    assert "Business Standard reported in 2021" in wikitext
    assert "Amar Ujala reported in 2023" in wikitext
    assert "Bovine ICM derived cells express the Oct4 ortholog" in wikitext
    assert "Reproductive Biotechnology in Buffalo" in wikitext
    assert "chief scientist of the project" in wikitext
    assert "orcid.org/0000-0002-0943-7306" not in wikitext
    assert wikitext.index("Theriogenology in 2024") < wikitext.index("published in Cellular Reprogramming")


def test_audit_accepts_sourced_research_stay_as_career_activity():
    annual = _source("https://institute.example.test/annual-report", independent=False)
    news_one = _source("https://news.example.test/a")
    news_two = _source("https://news.example.net/b")
    profile = PersonProfile(
        name="Example Person",
        sources=[annual, news_one, news_two],
        claims=[
            Claim(
                field="career",
                text="The institute recorded Example Person’s research stay in Germany in 2011",
                source_url=annual.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                field="known_for",
                text="Reported a nationally covered scientific milestone in the press",
                source_url=news_one.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                field="known_for",
                text="Led an internationally recognised research collaboration",
                source_url=news_two.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
        ],
    )

    audit = audit_profile(profile)

    assert audit.ready
    assert audit.eligible_claim_count == 3
    assert any(item.claim.field == "career" for item in audit.evidence)


def test_claim_draft_approval_is_a_separate_persisted_action(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.claims[0].draft_approved = False
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear"}})

    approved = backend_main.verify_claim(
        profile.name,
        backend_main.VerifyClaimRequest(claim_index=0, action="approve_draft"),
    )
    removed = backend_main.verify_claim(
        profile.name,
        backend_main.VerifyClaimRequest(claim_index=0, action="remove_draft"),
    )

    assert approved["claim"]["draft_approved"] is True
    assert removed["claim"]["draft_approved"] is False
    assert json.loads((tmp_path / "Example_Person.json").read_text())["profile"]["claims"][0]["draft_approved"] is False


def test_draft_endpoint_uses_server_session_and_persists_output(tmp_path, monkeypatch):
    profile = _ready_profile()
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear", "url": None, "note": None}})

    result = backend_main.generate_draft(backend_main.DraftRequest(profile_name=profile.name))
    saved = json.loads((tmp_path / "Example_Person.json").read_text())

    assert result["audit"]["ready"] is True
    assert result["profile"]["wikitext_en"]
    assert saved["profile"]["wikitext_en"] == result["profile"]["wikitext_en"]
    assert saved["wiki_status"]["status"] == "clear"


def test_add_sourced_claim_binds_fact_to_verified_source(tmp_path, monkeypatch):
    profile = _ready_profile()
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear"}})
    src = profile.sources[0]

    result = backend_main.add_sourced_claim(
        backend_main.AddSourcedClaimRequest(
            profile_name=profile.name,
            url=src.url,
            field="birth_date",
            text="Born on 10 April 1963",
            date_context="1963",
        )
    )

    assert result["claim"]["verification"] == "confirmed"
    assert result["claim"]["source_url"] == src.url
    assert result["claim"]["draft_approved"] is False
    assert result["claim"]["trust_score"] >= 0.5


def test_add_sourced_claim_requires_existing_source(tmp_path, monkeypatch):
    profile = _ready_profile()
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear"}})

    with pytest.raises(HTTPException):
        backend_main.add_sourced_claim(
            backend_main.AddSourcedClaimRequest(
                profile_name=profile.name,
                url="https://not-in-session.test/x",
                field="position",
                text="Some fact",
            )
        )


def test_skip_suggestion_persists_url_so_discovery_stops_offering_it(tmp_path, monkeypatch):
    profile = _ready_profile()
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear"}})
    url = "https://skipped.test/report"

    result = backend_main.skip_suggestion({"profile_name": profile.name, "url": url})

    assert result["ok"] is True
    assert url in profile.skipped_sources
    assert url in json.loads((tmp_path / "Example_Person.json").read_text())["profile"]["skipped_sources"]

    backend_main.skip_suggestion({"profile_name": profile.name, "url": url})
    assert profile.skipped_sources.count(url) == 1


def test_add_source_rejects_normalized_url_variant(tmp_path, monkeypatch):
    profile = _ready_profile()
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear"}})

    with pytest.raises(HTTPException):
        backend_main.add_source(
            backend_main.AddSourceRequest(
                profile_name=profile.name,
                url="http://news.example.test/report",
            )
        )


def test_resume_never_repopulates_claims_from_stub_provider(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.claims = []
    payload = {
        "profile": json.loads(profile.model_dump_json()),
        "wiki_status": {"status": "clear", "url": None, "note": None},
    }
    (tmp_path / "Example_Person.json").write_text(json.dumps(payload))
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})
    monkeypatch.setattr("engine.llm.has_real_llm", lambda: False)

    result = backend_main.resume_session({"file": "Example_Person.json"})

    assert result["profile"]["claims"] == []


def test_independent_count_uses_distinct_outlets_not_article_urls():
    toi_one = _source("https://timesofindia.indiatimes.com/a")
    toi_two = _source("https://timesofindia.indiatimes.com/b")
    ndtv = _source("https://www.ndtv.com/c")
    institution = _source("https://cirb.res.in/staff", independent=False)
    profile = PersonProfile(
        name="Example Person",
        sources=[toi_one, toi_two, ndtv, institution],
        claims=[
            Claim(
                field="position",
                text="Principal Scientist at Example Institute",
                source_url=institution.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                field="known_for",
                text="Led the first independently reported research project",
                source_url=toi_one.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                field="known_for",
                text="Led a second independently reported research project",
                source_url=toi_two.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                field="known_for",
                text="Led a third independently reported research project",
                source_url=ndtv.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
        ],
    )

    assert audit_profile(profile).independent_source_count == 2


def test_verified_amar_ujala_report_counts_as_independent_news():
    report = _source("https://www.amarujala.com/haryana/rewari/example")
    profile = PersonProfile(
        name="Example Person",
        sources=[report],
        claims=[
            Claim(
                field="position",
                text="Retired as a principal scientist at Example Institute in 2025",
                source_url=report.url,
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
        ],
    )

    assert audit_profile(profile).independent_source_count == 1
