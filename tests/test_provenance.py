"""Unit tests for Strict Provenance & Trust Scoring engine."""
import pytest
from engine.models import Source, Claim, SourceReliability, VerificationState
from engine.provenance import get_domain_trust, classify_source_provenance, evaluate_claim_trust
from engine.notability import score_notability


def test_domain_trust_classification():
    assert get_domain_trust("https://www.nature.com/articles/123") == "high"
    assert get_domain_trust("https://news.bbc.co.uk/world") == "high"
    assert get_domain_trust("https://mit.edu/faculty/jdoe") == "high"
    assert get_domain_trust("https://en.wikipedia.org/wiki/Test") == "medium"
    assert get_domain_trust("https://johndoe.medium.com/post") == "untrusted"
    assert get_domain_trust("https://unknownblog.com/page") == "low"
    assert get_domain_trust("https://www.hindi.news18.com/news/haryana") == "high"
    assert get_domain_trust("https://haryana.punjabkesari.in/haryana/news") == "high"
    assert get_domain_trust("https://livevns.news/state/haryana") == "high"
    assert get_domain_trust("https://sgttimes.com/faculty") == "medium"


def test_source_provenance_classification():
    # Authored publication
    s_pub = Source(
        url="https://doi.org/10.1038/s41586-020-0000-0",
        title="A groundbreaking paper in Nature",
        publisher="Nature Publishing Group",
        fetched_by="semantic_scholar"
    )
    classified_pub = classify_source_provenance(s_pub, "Jane Doe")
    assert classified_pub.provenance_category == "authored_publication"
    assert classified_pub.is_independent is False

    # Institutional bio
    s_bio = Source(
        url="https://cs.mit.edu/people/faculty/jane-doe",
        title="Jane Doe - Professor of Computer Science",
        publisher="MIT CSIL"
    )
    classified_bio = classify_source_provenance(s_bio, "Jane Doe")
    assert classified_bio.provenance_category == "institutional_bio"
    assert classified_bio.is_independent is False

    # Independent secondary news
    s_news = Source(
        url="https://www.bbc.com/news/technology-123456",
        title="MIT Researcher Wins Prestigious Turing Award",
        publisher="BBC News"
    )
    classified_news = classify_source_provenance(s_news, "Jane Doe")
    assert classified_news.provenance_category == "independent_secondary"
    assert classified_news.is_independent is True
    assert classified_news.reliability == SourceReliability.reliable_secondary


def test_academic_indexes_never_count_as_independent_news():
    for url in (
        "https://pubmed.ncbi.nlm.nih.gov/12345/",
        "https://www.sciencedirect.com/author/123/jane-doe",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC123/",
        "https://www.researchgate.net/publication/123_title",
    ):
        source = classify_source_provenance(Source(
            url=url,
            title="Authored research record",
            publisher="Academic index",
            fetched_by="google_search",
        ))
        assert source.provenance_category == "authored_publication"
        assert source.is_independent is False
        assert source.reliability == SourceReliability.primary


def test_search_discovery_does_not_make_unknown_site_independent():
    source = classify_source_provenance(Source(
        url="https://example-low-trust.test/profile",
        title="Search result",
        publisher="Unknown publisher",
        fetched_by="google_search",
    ))

    assert source.provenance_category == "general_web"
    assert source.reliability != SourceReliability.reliable_secondary
def test_claim_trust_evaluation():
    s_news = Source(
        url="https://www.bbc.com/news/technology-123456",
        title="MIT Researcher Wins Award",
        publisher="BBC News"
    )
    s_news = classify_source_provenance(s_news)

    c1 = Claim(
        text="Jane Doe was awarded the Turing Award",
        field="award",
        source_url=s_news.url,
        date_context="2022",
        verification=VerificationState.confirmed
    )
    eval_c1 = evaluate_claim_trust(c1, s_news)
    assert eval_c1.trust_score >= 0.8
    assert eval_c1.provenance_status == "verified_independent"
    assert eval_c1.is_independent is True

    # Primary sourced claim
    s_bio = Source(
        url="https://cs.mit.edu/people/faculty/jane-doe",
        title="Jane Doe Bio",
        publisher="MIT"
    )
    s_bio = classify_source_provenance(s_bio)
    c2 = Claim(
        text="Joined MIT faculty in 2010",
        field="position",
        source_url=s_bio.url
    )
    eval_c2 = evaluate_claim_trust(c2, s_bio)
    assert eval_c2.provenance_status == "primary_sourced"
    assert eval_c2.is_independent is False


def test_strict_notability_independence():
    # Only independent secondary sources count toward RS count
    s1 = Source(
        url="https://www.nytimes.com/2023/profile.html",
        title="NYT Feature",
        publisher="New York Times",
        human_verified=True,
        coverage_depth="significant",
    )
    s2 = Source(
        url="https://cs.mit.edu/people/jane",
        title="Faculty Bio",
        publisher="MIT",
        human_verified=True
    )
    claim = Claim(
        text="Jane Doe received a major research award",
        field="award",
        source_url=s1.url,
        verification=VerificationState.confirmed,
    )
    res = score_notability("Jane Doe", [s1, s2], [claim])
    # s1 supports a confirmed claim; s2 is an institutional bio and does not count.
    assert res.rs_count == 1
    assert res.label == "Weak coverage"


def test_notability_requires_confirmed_claims_and_deduplicates_outlets():
    sources = [
        Source(
            url="https://www.nytimes.com/2023/one.html",
            title="First feature",
            publisher="New York Times",
            coverage_depth="significant",
            human_verified=True,
        ),
        Source(
            url="https://www.nytimes.com/2024/two.html",
            title="Second feature",
            publisher="New York Times",
            coverage_depth="significant",
            human_verified=True,
        ),
    ]
    claims = [
        Claim(
            text="Jane Doe led a documented research programme",
            field="known_for",
            source_url=sources[0].url,
            verification=VerificationState.confirmed,
        ),
        Claim(
            text="Jane Doe later expanded the programme",
            field="known_for",
            source_url=sources[1].url,
            verification=VerificationState.confirmed,
        ),
    ]

    assert score_notability("Jane Doe", sources, []).rs_count == 0
    assert score_notability("Jane Doe", sources, claims).rs_count == 1


def test_notability_keeps_unassessed_candidates_out_of_score():
    source = Source(
        url="https://www.nytimes.com/2025/profile.html",
        title="A feature awaiting editorial review",
        publisher="New York Times",
        human_verified=True,
    )
    claim = Claim(
        text="Jane Doe led a documented programme",
        field="known_for",
        source_url=source.url,
        verification=VerificationState.confirmed,
    )

    result = score_notability("Jane Doe", [source], [claim])

    assert result.rs_count == 0
    assert result.candidate_count == 1
    assert result.label == "Coverage needs review"


def test_notability_deduplicates_syndicated_editorial_origins():
    sources = [
        Source(
            url=f"https://{host}/story",
            title="Syndicated feature",
            publisher=host,
            human_verified=True,
            coverage_depth="significant",
            editorial_origin="PTI story 2025-01",
        )
        for host in ("ndtv.com", "theprint.in")
    ]
    claims = [
        Claim(
            text=f"Jane Doe led programme {index}",
            field="known_for",
            source_url=source.url,
            verification=VerificationState.confirmed,
        )
        for index, source in enumerate(sources)
    ]

    result = score_notability("Jane Doe", sources, claims)

    assert result.rs_count == 1
    assert result.candidate_count == 1
def test_icar_and_cirb_reports_are_institutional_primary_sources():
    for url in (
        "https://cirb.res.in/reports/annual.pdf",
        "https://icar.org.in/award-citations.pdf",
        "https://icar.gov.in/node/123",
    ):
        source = classify_source_provenance(Source(
            url=url,
            title="Official institutional report",
            publisher="Indian Council of Agricultural Research",
        ))
        assert source.provenance_category == "institutional_bio"
        assert source.reliability == SourceReliability.primary
        assert source.is_independent is False


def test_record_registries_are_primary_and_non_independent():
    source = classify_source_provenance(Source(
        url="https://indiabookofrecords.in/maximum-buffalo-clones-produced/",
        title="Maximum buffalo clones produced",
        publisher="India Book of Records",
        fetched_by="google_search",
    ))

    assert source.provenance_category == "record_registry"
    assert source.reliability == SourceReliability.primary
    assert source.is_independent is False


def test_meaningful_redirect_detection():
    from engine.relevance import is_meaningful_redirect
    assert is_meaningful_redirect(
        "http://www.jagran.com/a/slug-13350123.html",
        "https://jagran.com/a/slug-13350123.html") is False  # scheme + www normalisation
    assert is_meaningful_redirect(
        "https://m.jagran.com/a/slug-13350123.html",
        "https://www.jagran.com/a/slug-13350123.html") is False  # mobile subdomain
    assert is_meaningful_redirect(
        "https://amp.jagran.com/a/slug-13350123.html",
        "https://www.jagran.com/a/slug-13350123.html") is False  # amp subdomain
    assert is_meaningful_redirect(
        "https://jagran.com/a/slug-13350123.html",
        "https://jagran.com/a/slug-13350123.html/amp") is False  # AMP variant
    assert is_meaningful_redirect(
        "https://trib.al/xyz", "https://www.tribuneindia.com/news/some-article") is False  # shortener
    assert is_meaningful_redirect(
        "https://doi.org/10.1000/xyz", "https://publisher.example/xyz") is False  # DOI resolver
    assert is_meaningful_redirect(
        "https://jagran.com/a/slug.html?utm_source=1",
        "https://jagran.com/a/slug.html") is False  # query params only
    # The trap: same domain, different article.
    assert is_meaningful_redirect(
        "https://www.jagran.com/haryana/hisar-gaurav-13350123.html",
        "https://www.jagran.com/haryana/unrelated-2015-article-99999999.html") is True
    # Landed on a different site entirely.
    assert is_meaningful_redirect(
        "https://jagran.com/a/x.html", "https://theprint.in/b/y.html") is True
    assert is_meaningful_redirect("https://jagran.com/a/x.html", "") is False


def test_fetch_url_source_flags_silent_redirect_trap(monkeypatch):
    from engine.researcher import fetch_url_source
    from engine.fetcher import FetchResult

    def fake_fetch(url):
        return FetchResult(
            url,
            "text of an unrelated 2015 article",
            method="direct",
            raw_html="<html><title>Other article</title></html>",
            final_url="https://www.jagran.com/haryana/unrelated-2015-article-99999999.html",
        )

    monkeypatch.setattr("engine.fetcher.fetch_url", fake_fetch)
    source, blocked = fetch_url_source(
        "https://www.jagran.com/haryana/hisar-gaurav-13350123.html", "Prem Singh Yadav")

    assert blocked is False
    assert source.redirected_to == "https://www.jagran.com/haryana/unrelated-2015-article-99999999.html"
    assert source.relevance_flag == "uncertain"


def test_fetch_url_source_ignores_normal_redirects(monkeypatch):
    from engine.researcher import fetch_url_source
    from engine.fetcher import FetchResult

    def fake_fetch(url):
        return FetchResult(
            url,
            "text",
            method="direct",
            raw_html="<html><title>Title</title></html>",
            final_url="https://jagran.com/a/slug-13350123.html",  # https normalisation only
        )

    monkeypatch.setattr("engine.fetcher.fetch_url", fake_fetch)
    source, blocked = fetch_url_source(
        "http://www.jagran.com/a/slug-13350123.html", "Prem Singh Yadav")

    assert blocked is False
    assert source.redirected_to is None
    assert source.relevance_flag == "unscored"

def test_source_assessment_requires_verification_and_persists():
    from fastapi import HTTPException
    from backend import store
    from backend.routes_research import assess_source
    from backend.schemas import AssessSourceRequest
    from engine.models import PersonProfile

    source = Source(
        url="https://www.nytimes.com/profile",
        title="Profile",
        publisher="New York Times",
    )
    profile = PersonProfile(name="Jane Doe", session_id="jane-1", sources=[source])
    store._sessions["jane-1"] = profile

    request = AssessSourceRequest(
        profile_name="jane-1",
        url=source.url,
        coverage_depth="significant",
        editorial_origin="NYT profile",
        research_notes="Substantial independent profile.",
    )
    with pytest.raises(HTTPException, match="Verify the source"):
        assess_source(request)

    source.human_verified = True
    result = assess_source(request)

    assert result["source"]["coverage_depth"] == "significant"
    assert profile.sources[0].editorial_origin == "NYT profile"
    assert profile.sources[0].research_notes == "Substantial independent profile."
