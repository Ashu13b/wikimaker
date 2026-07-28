"""Unit tests for Strict Provenance & Trust Scoring engine."""
import pytest
from engine.models import Source, Claim, PersonProfile, SourceReliability, VerificationState
from engine.provenance import get_domain_trust, classify_source_provenance, evaluate_claim_trust
from engine.notability import score_notability


def test_domain_trust_classification():
    assert get_domain_trust("https://www.nature.com/articles/123") == "high"
    assert get_domain_trust("https://news.bbc.co.uk/world") == "high"
    assert get_domain_trust("https://mit.edu/faculty/jdoe") == "high"
    assert get_domain_trust("https://en.wikipedia.org/wiki/Test") == "medium"
    assert get_domain_trust("https://johndoe.medium.com/post") == "untrusted"
    assert get_domain_trust("https://unknownblog.com/page") == "low"


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
        human_verified=True
    )
    s2 = Source(
        url="https://cs.mit.edu/people/jane",
        title="Faculty Bio",
        publisher="MIT",
        human_verified=True
    )
    res = score_notability("Jane Doe", [s1, s2])
    # s1 is independent secondary (high domain trust), s2 is institutional bio (primary)
    assert res.rs_count == 1
