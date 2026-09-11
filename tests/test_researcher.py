from unittest.mock import patch

from engine.models import Source, SourceReliability
from engine.researcher import _disambiguator, _sweep_news, targeted_slot_search


def _result(url: str) -> Source:
    return Source(
        url=url,
        title="Report about Example Person",
        publisher="Example News",
        reliability=SourceReliability.reliable_secondary,
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



def test_targeted_award_search_never_falls_back_to_education_queries():
    queries = []

    def fake_search(query: str):
        queries.append(query)
        return []

    with patch("engine.researcher._search_web", side_effect=fake_search):
        targeted_slot_search(
            "Prem Singh Yadav",
            "award",
            field="Animal biotechnology",
            affiliation="ICAR-CIRB Hisar",
        )

    assert queries
    assert all("ICAR" in query for query in queries)
    assert any("पुरस्कार" in query for query in queries)
    assert not any("alumni graduation" in query for query in queries)

def test_try_browser_server_probes_unified_mount_first(monkeypatch):
    from engine import fetcher
    from engine.fetcher import _try_browser_server

    calls = []

    class FakeResp:
        def __init__(self, body):
            self._body = body
        def json(self):
            return self._body
        def ok(self):
            return True

    def fake_get(url, **kw):
        calls.append(url)
        if url.endswith("/browser/status"):
            return FakeResp({"running": True, "headed": False, "url": None})
        if url.endswith("/status"):
            return FakeResp({"running": False, "headed": False, "url": None})
        if url.endswith("/navigate"):
            return FakeResp({"url": "https://example.test/x", "title": "X"})
        if url.endswith("/content"):
            return FakeResp({"url": "https://example.test/x", "text": "A real rendered article." * 20})
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(fetcher.requests, "get", fake_get)
    monkeypatch.setattr(fetcher.requests, "post", lambda *a, **kw: FakeResp({"url": "x", "title": "X"}))

    result = _try_browser_server("https://example.test/x")

    assert result is not None
    assert result.method == "browser"
    assert "http://localhost:3890/browser" in calls[0]
    assert "localhost:7070" not in calls


def test_try_browser_server_returns_none_when_no_browser_running(monkeypatch):
    from engine import fetcher

    def fake_get(url, **kw):
        return type("R", (), {"json": lambda self: {"running": False}})()
    monkeypatch.setattr(fetcher.requests, "get", fake_get)

    assert fetcher._try_browser_server("https://example.test/x") is None


def test_junk_source_url_filter():
    from engine.researcher import is_junk_source_url

    assert is_junk_source_url(
        "https://www.tribuneindia.com/sortd-service/imaginary/v22-01/jpg/large/high?url=x")
    assert is_junk_source_url("https://example.com/photo.jpg")
    assert not is_junk_source_url(
        "https://www.icmr.gov.in/former-director-generals")
    assert not is_junk_source_url("https://timesofindia.indiatimes.com/city/nagpur/gmc-host-event")


def test_pick_author_id_returns_none_when_nothing_validates(monkeypatch):
    from engine import researcher

    candidates = [
        {"authorId": "111", "paperCount": 500, "affiliations": []},
        {"authorId": "222", "paperCount": 3, "affiliations": []},
    ]

    class _Papers:
        def raise_for_status(self): pass
        def json(self):
            return {"data": [{"externalIds": {"DOI": "10.1/x"}}]}

    monkeypatch.setattr(researcher.requests, "get", lambda *a, **k: _Papers())
    monkeypatch.setattr(
        "engine.author_check.check_doi_authors",
        lambda doi, name, affil: {"status": "wrong_person"},
    )

    assert researcher._pick_author_id(candidates, "Some Person", "") is None


def test_add_source_with_client_text(monkeypatch):
    from backend.routes_research import add_source
    from backend.schemas import AddSourceRequest
    from engine.models import PersonProfile
    from backend import store

    profile = PersonProfile(name="Test Researcher", session_id="py-test-1234")
    monkeypatch.setattr(store, "_sessions", {profile.session_id: profile})
    monkeypatch.setattr(store, "_save_session", lambda *a: None)

    req = AddSourceRequest(
        profile_name="py-test-1234",
        url="https://hindustantimes.com/article/123",
        title="Custom Article Title",
        text="Dr. Researcher led the breakthrough project at the institute.",
    )

    res = add_source(req)
    assert res["blocked"] is False
    assert len(profile.sources) == 1
    assert profile.sources[0].title == "Custom Article Title"
    assert profile.sources[0].fetched_by == "browser"
    assert "breakthrough project" in profile.sources[0].snippet
