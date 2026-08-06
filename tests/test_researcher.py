from unittest.mock import patch

from engine.models import Source
from engine.researcher import _disambiguator, _sweep_news


def _result(url: str) -> Source:
    return Source(
        url=url,
        title="Report about Example Person",
        publisher="Example News",
        reliability="reliable_secondary",
        fetched_by="duckduckgo",
    )


def test_disambiguator_drops_institutional_stopwords():
    assert _disambiguator(
        "ICAR - Central Institute for Research on Buffaloes (CIRB), Hisar",
        "Animal biotechnology",
    ) == "ICAR Buffaloes"
    assert _disambiguator("University of California", "Physics") == "California"
    assert _disambiguator(None, "Computational biology") == "Computational biology"


def test_news_sweep_issues_site_restricted_and_hindi_queries():
    def fake_search(query: str):
        if "site:ndtv.com" in query:
            return [_result("https://www.ndtv.com/a"), _result("https://www.ndtv.com/b")]
        return [_result("https://example.test/other")]

    with patch("engine.researcher._search_web", side_effect=fake_search):
        sources = _sweep_news("Example Person", "Example Institute", "Science")

    urls = {s.url for s in sources}
    assert "https://www.ndtv.com/a" in urls
    assert "https://www.ndtv.com/b" in urls


def test_news_sweep_deduplicates_across_queries():
    def fake_search(query: str):
        return [_result("https://example.test/dup")]

    with patch("engine.researcher._search_web", side_effect=fake_search):
        sources = _sweep_news("Example Person", None, None)

    assert len(sources) == 1


def test_news_sweep_respects_limit():
    calls = {"n": 0}

    def fake_search(query: str):
        calls["n"] += 1
        return [_result(f"https://example.test/{calls['n']}")]

    with patch("engine.researcher._search_web", side_effect=fake_search):
        sources = _sweep_news("Example Person", None, None, limit=3)

    assert len(sources) == 3
    assert calls["n"] == 3
