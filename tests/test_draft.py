import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend import main as backend_main
from backend import store
from engine.models import Claim, PersonProfile, Source, SourceReliability, VerificationState
from wiki.draft import audit_profile, render_draft, _citation
from wiki.draft_verifier import extract_draft_links, check_draft_links


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


def test_audit_warns_when_achievement_claim_rests_on_primary_source():
    profile = _ready_profile()
    institution = _source("https://institute.example.test/announcement", independent=False)
    profile.sources.append(institution)
    profile.claims.append(Claim(
        field="award",
        text="Received the Outstanding Scientist Award from the institute",
        source_url=institution.url,
        verification=VerificationState.confirmed,
        draft_approved=True,
    ))

    audit = audit_profile(profile)

    assert audit.ready
    warning = next((w for w in audit.warnings if w.code == "achievement_claim_not_independent"), None)
    assert warning is not None
    assert warning.count == 1


def test_audit_no_achievement_warning_when_sources_are_independent():
    profile = _ready_profile()

    audit = audit_profile(profile)

    assert audit.ready
    assert not any(w.code == "achievement_claim_not_independent" for w in audit.warnings)


def test_research_action_rule_accepts_common_research_verbs():
    profile = _ready_profile()
    news = _source("https://news.example.test/report2")
    profile.sources.append(news)
    for text in (
        "A CIRB team found the semen profiles of cloned buffalo bulls to be comparable to non-cloned bulls",
        "In 2024 the institute reported a demand for the cloned bull's semen as far as China",
        "Yadav co-discovered Murrah bull male fertility genetic variants deposited in GenBank",
        "In 2022 Hisar Gaurav weighed 950 kg and remained physically fit and active at age seven",
    ):
        claim = Claim(
            field="known_for",
            text=text,
            source_url=news.url,
            verification=VerificationState.confirmed,
            draft_approved=True,
        )
        profile.claims.append(claim)

    audit = audit_profile(profile)

    assert audit.ready
    assert not any(e.code == "research_claim_has_no_subject_action" for e in audit.exclusions)


def test_birth_noise_rule_scans_source_title_too():
    # A clean-text birth claim sourced to a cloned-calf article must be caught
    # as describing the animal, not the person.
    animal_src = _source("https://cirb.res.in/news/cloned-calf-born", independent=False)
    animal_src.title = "ICAR-CIRB celebrates first birthday of cloned calf Hisar-Gaurav"
    profile = _ready_profile()
    profile.sources.append(animal_src)
    profile.claims.append(Claim(
        field="birth_date",
        text="Born on December 11, 2015",
        source_url=animal_src.url,
        verification=VerificationState.confirmed,
        draft_approved=True,
    ))

    audit = audit_profile(profile)

    assert any(e.code == "claim_appears_to_describe_animal" for e in audit.exclusions)


def test_human_birth_claim_not_blocked_by_animal_rule():
    # A real person birth from a human-roster source must still pass.
    roster = _source("https://cirb.res.in/staff-list-2023", independent=False)
    roster.title = "ICAR-CIRB Scientists Remunerations 2023"
    profile = _ready_profile()
    profile.sources.append(roster)
    profile.claims.append(Claim(
        field="birth_date",
        text="Born on 10 April 1963",
        source_url=roster.url,
        verification=VerificationState.confirmed,
        draft_approved=True,
    ))

    audit = audit_profile(profile)

    assert audit.ready
    assert not any(e.code == "claim_appears_to_describe_animal" for e in audit.exclusions)


def test_renderer_cites_every_included_claim_and_never_fills_biography_gaps():
    profile = _ready_profile()
    wikitext = render_draft(profile)

    assert "'''Example Person''' is an Indian scientist" in wikitext
    assert all("<ref" in line for line in wikitext.splitlines() if line.startswith("* "))
    assert "{{citation needed}}" not in wikitext
    assert "joined the Indian Council of Agricultural Research" not in wikitext
    assert "file:///" not in wikitext



def test_infobox_only_emits_fields_with_draft_approved_evidence():
    profile = _ready_profile()
    profile.birth_date = "10 April 1963"
    profile.birth_place = "Example Village"
    profile.nationality = "Indian"

    wikitext = render_draft(profile)

    assert "| birth_date =" not in wikitext
    assert "| birth_place =" not in wikitext
    assert "| nationality =" not in wikitext
    assert "| field = Animal biotechnology" in wikitext


def test_renderer_surfaces_curated_award_in_lead_without_repeating_section():
    profile = _ready_profile()
    award_source = _source("https://news.example.test/national-award")
    profile.sources.append(award_source)
    profile.claims.append(Claim(
        field="award",
        text="Received the National Example Prize for interdisciplinary research",
        source_url=award_source.url,
        verification=VerificationState.confirmed,
        draft_approved=True,
    ))

    wikitext = render_draft(profile)

    assert wikitext.count("Received the National Example Prize") == 1
    assert "==Awards and recognition==" not in wikitext


def test_renderer_includes_approved_achievement_in_research():
    profile = _ready_profile()
    source = _source("https://news.example.test/cloning-result")
    profile.sources.append(source)
    profile.claims.append(Claim(
        field="achievement",
        text="In 2020, the team produced seven clones of an elite buffalo bull",
        source_url=source.url,
        verification=VerificationState.confirmed,
        draft_approved=True,
    ))

    wikitext = render_draft(profile)

    assert "==Research==" in wikitext
    assert wikitext.count("produced seven clones") == 1


def test_renderer_uses_subject_specific_short_description():
    profile = _ready_profile()
    profile.nationality = "Canadian"
    profile.field = "Quantum Physics and Optics"

    wikitext = render_draft(profile)

    assert "{{Short description|Canadian quantum physics researcher}}" in wikitext
    assert "Animal cloning researcher" not in wikitext


def test_publication_first_author_study_is_bibliographic_and_sorted_by_claim_year():
    profile = _ready_profile()
    source = _source("https://journal.example.test/paper")
    source.date = "2025"
    profile.sources.append(source)
    profile.claims.append(Claim(
        field="publication",
        text="Yadav was first author of a 2005 study in Example Journal",
        source_url=source.url,
        verification=VerificationState.confirmed,
        draft_approved=True,
    ))

    audit = audit_profile(profile)
    wikitext = render_draft(profile, audit)

    assert not any(issue.code == "publication_claim_not_bibliographic" for issue in audit.exclusions)
    assert "Yadav was first author of a 2005 study" in wikitext

def test_dr_yadav_saved_session_produces_policy_filtered_draft():
    session_path = Path(__file__).parent / "fixtures" / "Prem_Singh_Yadav.json"
    profile = PersonProfile(**json.loads(session_path.read_text())["profile"])

    audit = audit_profile(profile)
    wikitext = render_draft(profile, audit)

    assert audit.ready
    assert audit.eligible_claim_count >= 28
    # Seven unsupported private-CV claims were removed from the fixture.
    assert audit.excluded_claim_count >= 91
    assert audit.independent_source_count >= 2
    assert "'''Prem Singh Yadav'''" in wikitext
    assert wikitext.count("{{cite web") >= 5
    assert "4 kg born through normal delivery" not in wikitext
    assert "file:///" not in wikitext
    assert "joined the Indian Council of Agricultural Research (ICAR) as a scientist in 1993" not in wikitext
    assert all("<ref" in line for line in wikitext.splitlines() if line.startswith("* "))
    assert wikitext.index("joining date of 12 April 1993") < wikitext.index("In 2018, The Tribune")
    assert "In 2018, The Tribune" in wikitext
    assert "In 2022, a PTI report" in wikitext
    assert "2024 annual report" in wikitext
    assert "retired as an ICAR-CIRB principal scientist in 2025" in wikitext
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
    profile.session_id = "py-example-person-test1"
    profile.claims[0].draft_approved = False
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.session_id: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.session_id: {"status": "clear"}})

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
    saved = json.loads((tmp_path / f"{profile.session_id}.json").read_text())
    assert saved["profile"]["claims"][0]["draft_approved"] is False


def test_unverified_claim_direct_draft_approval(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.session_id = "py-example-person-unverified-test"
    profile.claims[0].verification = VerificationState.unverified
    profile.claims[0].draft_approved = False
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.session_id: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.session_id: {"status": "clear"}})

    approved = backend_main.verify_claim(
        profile.name,
        backend_main.VerifyClaimRequest(claim_index=0, action="approve_draft"),
    )

    assert approved["claim"]["verification"] == "confirmed"
    assert approved["claim"]["draft_approved"] is True


def test_batch_verify_claims(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.session_id = "py-example-person-batch-test"
    for c in profile.claims:
        c.verification = VerificationState.unverified
        c.draft_approved = False
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.session_id: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.session_id: {"status": "clear"}})

    # Batch approve usable
    res = backend_main.batch_verify_claims(
        profile.name,
        backend_main.BatchVerifyClaimsRequest(action="approve_all_usable"),
    )
    assert res["updated_count"] == len(profile.claims)
    assert all(c["draft_approved"] is True for c in res["profile"]["claims"])

    # Batch confirm all
    profile.claims[0].verification = VerificationState.unverified
    profile.claims[0].draft_approved = False
    res = backend_main.batch_verify_claims(
        profile.name,
        backend_main.BatchVerifyClaimsRequest(action="confirm_all"),
    )
    assert res["profile"]["claims"][0]["verification"] == "confirmed"
    assert res["profile"]["claims"][0]["draft_approved"] is False

    # Batch skip unverified
    profile.claims[0].verification = VerificationState.unverified
    res = backend_main.batch_verify_claims(
        profile.name,
        backend_main.BatchVerifyClaimsRequest(action="skip_unverified"),
    )
    assert res["profile"]["claims"][0]["verification"] == "skipped"
    assert res["profile"]["claims"][0]["draft_approved"] is False


def test_edit_draft_text_action(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.session_id = "py-example-person-edit-draft-text"
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.session_id: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.session_id: {"status": "clear"}})

    res = backend_main.verify_claim(
        profile.name,
        backend_main.VerifyClaimRequest(
            claim_index=0,
            action="edit_draft_text",
            edited_text="Custom encyclopedic draft wording for lead.",
        ),
    )

    assert res["claim"]["draft_text"] == "Custom encyclopedic draft wording for lead."
    assert res["claim"]["draft_approved"] is True


def test_publishers_registry_and_subdomains():
    from engine.publishers import (
        is_independent_secondary_news,
        is_primary_or_institutional,
        extract_domain,
    )

    # Subdomains & domains
    assert extract_domain("https://www.hindustantimes.com/world/story.html") == "hindustantimes.com"
    assert extract_domain("http://timesofindia.indiatimes.com/city/delhi") == "timesofindia.indiatimes.com"
    assert is_independent_secondary_news("https://www.thehindu.com/news/national/") is True
    assert is_independent_secondary_news("https://edition.cnn.com/article") is False  # not in set
    assert is_independent_secondary_news("https://m.amarujala.com/haryana/") is True
    assert is_primary_or_institutional("https://cirb.res.in/about-us") is True
    assert is_primary_or_institutional("https://icar.gov.in/node/123") is True
    # Institutional is never independent secondary news
    assert is_independent_secondary_news("https://cirb.res.in/news") is False


def test_draft_endpoint_uses_server_session_and_persists_output(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.session_id = "py-example-person-test2"
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.session_id: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.session_id: {"status": "clear", "url": None, "note": None}})

    result = backend_main.generate_draft(backend_main.DraftRequest(profile_name=profile.name))
    saved = json.loads((tmp_path / f"{profile.session_id}.json").read_text())

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
    profile.session_id = "py-example-person-test3"
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.session_id: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.session_id: {"status": "clear"}})
    url = "https://skipped.test/report"

    result = backend_main.skip_suggestion({"profile_name": profile.name, "url": url})

    assert result["ok"] is True
    assert url in profile.skipped_sources
    saved = json.loads((tmp_path / f"{profile.session_id}.json").read_text())
    assert url in saved["profile"]["skipped_sources"]

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
    monkeypatch.setattr("wiki.wiki_check.check_existing_page", lambda title: type("S", (), {"model_dump": lambda self: {"status": "clear", "url": None, "note": None}})())

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


_SAMPLE_DRAFT = (
    "{{Draft article}}\n"
    "'''Example Person''' is a scientist<ref name=\"src-one\">{{cite web|url=https://news.example.test/report|"
    "title=Report on Example Person|website=Example News|date=2024}}</ref>.\n"
    "==Research==\n"
    "* Led a study<ref name=\"src-two\">{{cite web|url=https://paywalled.example.test/paper|"
    "archive-url=https://web.archive.org/web/2024/https://paywalled.example.test/paper|"
    "title=Paywalled|website=Journal}}</ref>.\n"
    "* Repeated cite<ref name=\"src-one\" />.\n"
    "* Raw link [https://raw.example.test/bio Read the bio].\n"
    "==References==\n"
    "{{reflist}}\n"
)


def test_extract_draft_links_prefers_archive_and_deduplicates():
    links = extract_draft_links(_SAMPLE_DRAFT)

    assert [link.url for link in links] == [
        "https://news.example.test/report",
        "https://web.archive.org/web/2024/https://paywalled.example.test/paper",
        "https://raw.example.test/bio",
    ]
    assert links[0].label == "Report on Example Person"
    assert links[0].archived is False
    assert links[1].archived is True
    assert links[2].label == "Read the bio"


def test_extract_draft_links_handles_escaped_pipe_in_title():
    wikitext = ('Led a study<ref name="a">{{cite web|url=https://news.example.test/x|'
                'title=Title {{!}} with pipe|website=Example News}}</ref>.')
    links = extract_draft_links(wikitext)
    assert links[0].label == "Title | with pipe"


def test_citation_keeps_original_url_and_adds_archive_fields():
    from engine.models import Source
    source = Source(
        url="https://news.example.test/report",
        title="Report on Example Person",
        publisher="Example News",
        date="2024-01-05",
        archive_url="https://web.archive.org/web/20170407044036/http://www.news.example.test/report",
    )
    citation = _citation(source, set())
    assert "url=https://news.example.test/report" in citation
    assert "archive-url=https://web.archive.org/web/20170407044036/" in citation
    assert "archive-date=7 April 2017" in citation
    assert "date=5 January 2024" in citation


def test_title_clean_strips_truncation_before_publisher_suffix():
    from wiki.draft import _title_clean

    assert _title_clean("Telomerase Structure and Function, Activity and Its... | IntechOpen") == (
        "Telomerase Structure and Function, Activity and Its"
    )
    assert _title_clean("How Buffaloes Clone | Amar Ujala") == "How Buffaloes Clone | Amar Ujala"
    assert _title_clean("A plain title.") == "A plain title"


def test_check_draft_links_classifies_http_statuses(monkeypatch):
    import browser_server as bs
    monkeypatch.setattr(bs, "_running", False)

    class FakeResp:
        def __init__(self, code, url):
            self.status_code = code
            self.url = url
        def close(self):
            pass

    def fake_get(url, **kwargs):
        if "dead" in url:
            return FakeResp(404, url)
        if "blocked" in url:
            return FakeResp(403, url)
        if "498test" in url:
            return FakeResp(498, url)
        if "doi.org" in url:
            return FakeResp(403, url)
        return FakeResp(200, url)

    monkeypatch.setattr("requests.get", fake_get)
    results = check_draft_links([
        "https://news.example.test/report",
        "https://dead.example.test/x",
        "https://blocked.example.test/y",
        "https://web.archive.org/web/20240101000000/https://news.example.test/report",
        "https://web.archive.org/web/498test/https://news.example.test/x",
        "https://doi.org/10.1089/cell.2023.0003",
    ])

    assert results["https://news.example.test/report"]["status"] == "ok"
    assert results["https://dead.example.test/x"]["status"] == "dead"
    assert results["https://blocked.example.test/y"]["status"] == "blocked"
    assert results["https://web.archive.org/web/20240101000000/https://news.example.test/report"]["status"] == "ok"
    assert results["https://web.archive.org/web/498test/https://news.example.test/x"]["status"] == "ok"
    assert results["https://doi.org/10.1089/cell.2023.0003"]["status"] == "ok"


def test_check_draft_links_uses_browser_for_uncertain_links(monkeypatch):
    import browser_server as bs
    monkeypatch.setattr(bs, "_running", True)
    captured = {}

    class FakeResp:
        def __init__(self, code, url):
            self.status_code = code
            self.url = url
        def close(self):
            pass

    def fake_get(url, **kwargs):
        if "blocked" in url:
            return FakeResp(403, url)
        return FakeResp(200, url)

    monkeypatch.setattr("requests.get", fake_get)

    def fake_dispatch(action, **kwargs):
        captured["action"] = action
        captured["urls"] = kwargs["urls"]
        return {u: {"status": "ok", "status_code": 200, "final_url": u} for u in kwargs["urls"]}

    monkeypatch.setattr(bs, "_dispatch", fake_dispatch)

    result = check_draft_links([
        "https://news.example.test/report",
        "https://blocked.example.test/y",
    ])

    assert result["https://news.example.test/report"]["status"] == "ok"
    assert result["https://blocked.example.test/y"]["status"] == "ok"
    assert captured["action"] == "link_status_page"
    assert captured["urls"] == ["https://blocked.example.test/y"]


def test_check_draft_links_keeps_requests_verdict_when_browser_errors(monkeypatch):
    import browser_server as bs
    monkeypatch.setattr(bs, "_running", True)

    def fake_dispatch(action, **kwargs):
        raise RuntimeError("browser thread died")

    monkeypatch.setattr(bs, "_dispatch", fake_dispatch)

    class FakeResp:
        def __init__(self, code, url):
            self.status_code = code
            self.url = url
        def close(self):
            pass

    monkeypatch.setattr("requests.get", lambda *a, **kw: FakeResp(403, a[0]))
    result = check_draft_links(["https://blocked.example.test/y"])

    assert result["https://blocked.example.test/y"]["status"] == "blocked"


def test_check_draft_links_skips_browser_when_all_ok(monkeypatch):
    import browser_server as bs
    monkeypatch.setattr(bs, "_running", True)
    dispatched = []

    def fake_dispatch(action, **kwargs):
        dispatched.append(action)
        raise AssertionError("browser must not be called for all-ok links")

    monkeypatch.setattr(bs, "_dispatch", fake_dispatch)

    class FakeResp:
        def __init__(self, code, url):
            self.status_code = code
            self.url = url
        def close(self):
            pass

    monkeypatch.setattr("requests.get", lambda *a, **kw: FakeResp(200, a[0]))
    result = check_draft_links(["https://news.example.test/a", "https://news.example.test/b"])

    assert dispatched == []
    assert all(v["status"] == "ok" for v in result.values())


def test_fetch_blocked_walks_blocked_sources_through_browser(tmp_path, monkeypatch):
    import browser_server as bs
    monkeypatch.setattr(bs, "_running", True)

    profile = _ready_profile()
    profile.sources.append(Source(
        url="https://blocked.example.test/paper",
        title="Paper", publisher="Example",
        reliability=SourceReliability.primary,
        snippet="",
        liveness="blocked",
    ))
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})

    navigated = []

    def fake_dispatch(action, **kwargs):
        if action == "navigate":
            navigated.append(kwargs["url"])
            return {"url": kwargs["url"], "title": "Paper"}
        if action == "content":
            return {"url": "https://blocked.example.test/paper",
                    "text": "Full rendered text about buffalo cloning at CIRB Hisar." * 4}
        raise AssertionError(f"unexpected action {action}")

    monkeypatch.setattr(bs, "_dispatch", fake_dispatch)

    result = backend_main.fetch_blocked({"profile_name": profile.name})

    assert navigated == ["https://blocked.example.test/paper"]
    assert result["fetched"] == ["https://blocked.example.test/paper"]
    assert result["walls"] == []
    source = profile.sources[-1]
    assert source.liveness == "alive"
    assert source.fetched_by == "browser"
    assert "buffalo cloning" in source.snippet


def test_fetch_blocked_stops_at_bot_wall(tmp_path, monkeypatch):
    import browser_server as bs
    monkeypatch.setattr(bs, "_running", True)

    profile = _ready_profile()
    blocked = Source(
        url="https://blocked.example.test/wall",
        title="Wall", publisher="Example",
        reliability=SourceReliability.primary,
        snippet="",
        liveness="blocked",
    )
    profile.sources.append(blocked)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})

    def fake_dispatch(action, **kwargs):
        if action == "navigate":
            return {"url": kwargs["url"], "title": "Wall"}
        if action == "content":
            return {"url": "https://blocked.example.test/wall",
                    "text": "Please verify you are human. Access denied by Cloudflare."}
        raise AssertionError(f"unexpected action {action}")

    monkeypatch.setattr(bs, "_dispatch", fake_dispatch)

    result = backend_main.fetch_blocked({"profile_name": profile.name})

    assert result["fetched"] == []
    assert result["walls"] == ["https://blocked.example.test/wall"]
    assert blocked.liveness == "blocked"


def test_draft_links_endpoint_extracts_and_checks(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.wikitext_en = _SAMPLE_DRAFT
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear"}})

    class FakeResp:
        def __init__(self):
            self.status_code = 200
            self.url = "https://news.example.test/report"
        def close(self):
            pass

    monkeypatch.setattr("requests.get", lambda url, **kwargs: FakeResp())

    result = backend_main.draft_links({"profile_name": profile.name})

    assert len(result["links"]) == 3
    assert all(link["status"] == "ok" for link in result["links"])
    assert result["links"][0]["url"] == "https://news.example.test/report"


def test_draft_verify_runs_checker_and_verifier(tmp_path, monkeypatch):
    import browser_server as bs
    monkeypatch.setattr(bs, "_running", False)
    profile = _ready_profile()
    profile.wikitext_en = _SAMPLE_DRAFT
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {profile.name: {"status": "clear"}})

    class FakeResp:
        def __init__(self):
            self.status_code = 200
            self.url = "https://news.example.test/report"
        def close(self):
            pass

    monkeypatch.setattr("requests.get", lambda url, **kwargs: FakeResp())

    result = backend_main.draft_verify({"profile_name": profile.name})

    assert "counts" in result["qa"]
    assert len(result["links"]) == 3
    assert all(link["status"] == "ok" for link in result["links"])
    assert isinstance(result["verified"], bool)


def test_draft_links_requires_generated_draft(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.wikitext_en = None
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})

    with pytest.raises(HTTPException) as exc:
        backend_main.draft_links({"profile_name": profile.name})
    assert exc.value.status_code == 400


def test_draft_preview_endpoint_returns_parsoid_html(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.wikitext_en = _SAMPLE_DRAFT
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})

    class FakeResp:
        text = '<div class="mw-parser-output"><p>Example</p></div>'
        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.post", lambda *a, **kw: FakeResp())

    result = backend_main.draft_preview({"profile_name": profile.name})

    assert result["html"] == '<div class="mw-parser-output"><p>Example</p></div>'


def test_draft_preview_propagates_renderer_failure(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.wikitext_en = _SAMPLE_DRAFT
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})

    class FakeResp:
        def raise_for_status(self):
            raise RuntimeError("parsoid down")

    monkeypatch.setattr("requests.post", lambda *a, **kw: FakeResp())

    with pytest.raises(HTTPException) as exc:
        backend_main.draft_preview({"profile_name": profile.name})
    assert exc.value.status_code == 502


def _qa_profile() -> PersonProfile:
    profile = _ready_profile()
    profile.wikitext_en = _SAMPLE_DRAFT
    return profile


def test_qa_flags_missing_structural_bits():
    from wiki.draft_qa import qa_draft

    report = qa_draft(_qa_profile())
    ids = [f.id for f in report.findings]
    assert "short_description" in ids
    assert "infobox" in ids
    assert "thin_lead" in ids
    assert report.passed is False


def test_qa_passes_well_formed_draft():
    from wiki.draft_qa import qa_draft

    profile = _qa_profile()
    cites = "\n".join(
        f"* Sentence number {i} of the article body<ref name=\"s{i}\">{{{{cite web|url=https://news.example.test/r{i}|"
        f"title=Report number {i}|website=Example News|date={i} May 2024}}}}</ref>."
        for i in range(10)
    )
    profile.wikitext_en = (
        "{{Draft article}}\n{{Short description|Indian scientist}}\n"
        "{{Infobox scientist|name = Example Person|field = Animal biotechnology}}\n"
        "'''Example Person''' is an Indian scientist who studies animal biotechnology<ref name=\"s1\" />. "
        "They led a cloning study at Example Institute<ref name=\"s2\" /> and reported a national milestone<ref "
        "name=\"s3\" />. The work was widely covered by the Indian press<ref name=\"s4\" />.\n"
        f"==Research==\n{cites}\n==References==\n{{{{reflist}}}}\n\n"
        "{{Authority control}}\n{{DEFAULTSORT:Person, Example}}\n[[Category:Living people]]\n"
    )
    report = qa_draft(profile)
    assert report.passed is True, [f.model_dump() for f in report.findings]


def test_qa_flags_dirty_titles_iso_dates_and_weak_sources():
    from wiki.draft_qa import qa_draft

    profile = _qa_profile()
    profile.wikitext_en = (
        "{{Short description|Indian scientist}}\n"
        "{{Infobox scientist|name = Example Person}}\n"
        "'''Example Person''' is a scientist<ref name=\"s1\">{{cite web|url=https://news.example.test/report|"
        "title=Report on Example Person | Example News|website=Example News|date=2024-05-03}}</ref>.\n"
        "==References==\n{{reflist}}\n"
    )
    profile.sources[2].reliability = SourceReliability.unreliable
    report = qa_draft(profile)
    ids = [f.id for f in report.findings]
    assert "dirty_title" in ids
    assert "iso_date" in ids
    assert "weak_source" in ids


def test_qa_no_draft_is_an_error():
    from wiki.draft_qa import qa_draft

    profile = _ready_profile()
    profile.wikitext_en = None
    report = qa_draft(profile)
    assert report.passed is False
    assert report.findings[0].id == "no_draft"


def test_qa_flags_attribution_chains():
    from wiki.draft_qa import qa_draft

    profile = _qa_profile()
    profile.wikitext_en = (
        "{{Short description|Indian scientist}}\n"
        "{{Infobox scientist|name = Example Person|field = Animal biotechnology}}\n"
        "'''Example Person''' is a scientist. Moneycontrol reported that the team cloned a bull"
        "<ref name=\"s1\">{{cite web|url=https://news.example.test/r1|title=Report|website=Example News|date=1 May 2024}}</ref>."
        " According to The Times, the work was a milestone<ref name=\"s2\">{{cite web|url=https://news.example.test/r2|title=More|website=Example News|date=2 May 2024}}</ref>.\n"
        "==References==\n{{reflist}}\n"
    )
    report = qa_draft(profile)
    finding = next((f for f in report.findings if f.id == "attribution_chain"), None)
    assert finding is not None
    assert finding.severity == "warning"
    assert "reported that" in finding.message
    assert "according to" in finding.message.lower()


def test_draft_qa_endpoint_lints_stored_draft(tmp_path, monkeypatch):
    profile = _ready_profile()
    profile.wikitext_en = _SAMPLE_DRAFT
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})

    result = backend_main.draft_qa({"profile_name": profile.name})

    assert result["passed"] is False
    ids = [f["id"] for f in result["findings"]]
    assert "short_description" in ids
    assert result["counts"]["error"] >= 1


def test_draft_qa_endpoint_requires_draft(tmp_path, monkeypatch):
    profile = _ready_profile()
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})

    with pytest.raises(HTTPException) as exc:
        backend_main.draft_qa({"profile_name": profile.name})
    assert exc.value.status_code == 400


def test_qa_flags_duplicate_approved_claims():
    from engine.models import Claim
    from wiki.draft_qa import qa_draft

    profile = _qa_profile()
    profile.claims = [
        Claim(
            field="known_for",
            text="In 2020 a research team led by Yadav produced seven clones of the elite bull M-29",
            draft_approved=True,
            source_url="https://news.example.test/r1",
        ),
        Claim(
            field="known_for",
            text="In 2020 a research team led by Yadav produced seven clones of the elite bull M-29",
            draft_approved=True,
            source_url="https://news.example.test/r2",
        ),
    ]
    report = qa_draft(profile)
    finding = next((f for f in report.findings if f.id == "duplicate_approved_claim"), None)
    assert finding is not None
    assert finding.severity == "warning"


def test_qa_flags_institutional_achievement_sources():
    from engine.models import Claim, Source, SourceReliability
    from wiki.draft_qa import qa_draft

    profile = _qa_profile()
    profile.sources = [
        Source(
            url="https://inst.example.test/award-bulletin.pdf",
            title="Institute Bulletin",
            publisher="Institute Internal",
            reliability=SourceReliability.reliable_secondary,
            is_independent=False,
            provenance_category="institutional_bio",
        )
    ]
    profile.claims = [
        Claim(
            field="award",
            text="Received the National Outstanding Team Award",
            draft_approved=True,
            source_url="https://inst.example.test/award-bulletin.pdf",
        )
    ]
    report = qa_draft(profile)
    finding = next((f for f in report.findings if f.id == "institutional_achievement_source"), None)
    assert finding is not None
    assert finding.severity == "warning"
    assert "Institute Internal" in finding.message
