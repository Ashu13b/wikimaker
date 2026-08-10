from unittest.mock import patch

from engine.llm import StubProvider
from engine.models import PersonProfile, Source, UrlSuggestion
from engine.suggester import _generate_multiyear_report_urls, is_profile_url, suggest_next_urls


def test_multiyear_sweep_never_fabricates_dois_or_publisher_urls():
    assert _generate_multiyear_report_urls("https://doi.org/10.48165/aru.2023.3.1.6") == []
    assert _generate_multiyear_report_urls("https://www.nature.com/articles/s41598-019-47909-8") == []
    assert _generate_multiyear_report_urls("https://pubmed.ncbi.nlm.nih.gov/37793222/") == []
    assert _generate_multiyear_report_urls("https://www.researchgate.net/publication/12345") == []


def test_multiyear_sweep_still_covers_institutional_report_series():
    urls = _generate_multiyear_report_urls(
        "https://cirb.res.in/wp-content/uploads/2018/07/CIRB-AR-2025.pdf"
    )
    assert len(urls) == 25
    assert "https://cirb.res.in/wp-content/uploads/2000/07/CIRB-AR-2025.pdf" in urls
    assert "https://cirb.res.in/wp-content/uploads/2018/07/CIRB-AR-2025.pdf" not in urls


def test_report_guesses_are_bounded_and_real_searches_still_rank():
    profile = PersonProfile(
        name="Example Person",
        affiliation="Example Institute",
        field="Science",
        missing_slots=["known_for"],
        sources=[
            Source(
                url="https://cirb.res.in/wp-content/uploads/2018/07/CIRB-AR-2025.pdf",
                title="Annual Report",
                publisher="CIRB",
            )
        ],
    )

    def fake_search(query: str):
        if "site:" in query:
            return [
                Source(
                    url=f"https://news.example/{abs(hash(query)) % 1000}",
                    title="Real news about Example Person",
                    publisher="Example News",
                    snippet="Example Person Example Institute Science award research",
                )
            ]
        return []

    with patch("engine.researcher._search_web", side_effect=fake_search):
        with patch("engine.llm.get_provider", return_value=StubProvider()):
            suggestions = suggest_next_urls(profile, max_results=6)

    urls = [x["url"] for x in suggestions]
    assert len(urls) <= 6
    assert any("news.example" in u for u in urls)
    assert sum("CIRB-AR-" in u for u in urls) <= 4

    # Every suggestion must satisfy the API contract — a key/value drift fails loudly.
    for s in suggestions:
        validated = UrlSuggestion(**s)
        assert validated.url == s["url"]
    assert all(set(s) <= set(UrlSuggestion.model_fields) for s in suggestions)


def test_generic_social_and_author_links_are_not_person_profiles():
    assert not is_profile_url("https://www.linkedin.com/company/example")
    assert not is_profile_url("https://www.linkedin.com/sharing/share-offsite/?url=x")
    assert not is_profile_url("https://example.test/author/administrator/")


def test_profile_link_suggestions_drop_generic_links():
    profile = PersonProfile(
        name="Example Person",
        affiliation="Example Institute",
        field="Animal science",
        sources=[Source(
            url="https://news.example/report",
            title="Example Person at Example Institute",
            publisher="Example News",
            profile_links=[
                "https://example.test/author/administrator/",
                "https://linkedin.com/company/example",
                "https://example.edu/staff/example-person/",
            ],
        )],
    )

    with patch("engine.suggester._search_queries", return_value=[]):
        suggestions = suggest_next_urls(profile)

    urls = {item["url"] for item in suggestions}
    assert "https://example.edu/staff/example-person/" in urls
    assert "https://example.test/author/administrator/" not in urls
    assert "https://linkedin.com/company/example" not in urls
