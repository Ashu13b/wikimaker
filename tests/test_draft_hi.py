"""Unit tests for deterministic Hindi draft generator."""
from engine.models import PersonProfile, Source, Claim, VerificationState, SourceReliability
from wiki.draft_hi import render_hindi_draft
from wiki.draft import audit_profile


def _sample_profile() -> PersonProfile:
    profile = PersonProfile(
        name="Prem Singh Yadav",
        full_name="Dr. Prem Singh Yadav",
        field="Animal Biotechnology",
        affiliation="ICAR-CIRB",
        nationality="Indian",
        known_for="Buffalo cloning",
        sources=[
            Source(
                url="https://www.thehindu.com/news/national/cirb-cloning-milestone",
                title="CIRB achieves cloning milestone",
                publisher="The Hindu",
                reliability=SourceReliability.reliable_secondary,
                is_independent=True,
                provenance_category="independent_secondary",
                human_verified=True,
            ),
            Source(
                url="https://www.tribuneindia.com/news/haryana/yadav-cloning-success",
                title="Tribune India: Yadav Cloning Success",
                publisher="The Tribune",
                reliability=SourceReliability.reliable_secondary,
                is_independent=True,
                provenance_category="independent_secondary",
                human_verified=True,
            ),
        ],
        claims=[
            Claim(
                text="Prem Singh Yadav is an Indian national",
                field="nationality",
                source_url="https://www.thehindu.com/news/national/cirb-cloning-milestone",
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                text="Prem Singh Yadav is a scientist researching Animal Biotechnology",
                field="field",
                source_url="https://www.thehindu.com/news/national/cirb-cloning-milestone",
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                text="Served as Principal Scientist at ICAR-CIRB",
                field="career",
                source_url="https://www.tribuneindia.com/news/haryana/yadav-cloning-success",
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                text="Led the team that cloned Hisar Gaurav buffalo calf",
                field="known_for",
                source_url="https://www.thehindu.com/news/national/cirb-cloning-milestone",
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
            Claim(
                text="Pioneered somatic cell nuclear transfer techniques in buffalo embryology",
                field="achievement",
                source_url="https://www.thehindu.com/news/national/cirb-cloning-milestone",
                verification=VerificationState.confirmed,
                draft_approved=True,
            ),
        ],
    )
    return profile


def test_render_hindi_draft_contains_hindi_infobox_and_sections():
    profile = _sample_profile()
    audit = audit_profile(profile)
    assert audit.ready

    wikitext_hi = render_hindi_draft(profile, audit)
    assert "{{ज्ञानसन्दूक वैज्ञानिक" in wikitext_hi
    assert "| नाम = Prem Singh Yadav" in wikitext_hi
    assert "| राष्ट्रीयता = भारतीय" in wikitext_hi
    assert "| संस्थान = ICAR-CIRB" in wikitext_hi
    assert "'''Prem Singh Yadav''' एक भारतीय वैज्ञानिक हैं" in wikitext_hi
    assert "== करियर ==" in wikitext_hi
    assert "== प्रमुख शोध एवं योगदान ==" in wikitext_hi
    assert "== सन्दर्भ ==" in wikitext_hi
    assert "[[श्रेणी:जीवित लोग]]" in wikitext_hi
    assert "[[श्रेणी:भारतीय वैज्ञानिक]]" in wikitext_hi
