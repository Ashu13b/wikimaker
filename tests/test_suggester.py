from unittest.mock import patch

from engine.llm import StubProvider
from engine.models import PersonProfile, Source
from engine.suggester import _generate_multiyear_report_urls, suggest_next_urls


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
