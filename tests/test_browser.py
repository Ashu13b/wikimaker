"""Tests for browser_server link adjudication — page-render verdicts for
links plain requests cannot classify."""

from browser_server import _page_link_status, browser_link_status


class _FakeResp:
    def __init__(self, status: int | None):
        self.status = status


class _FakePage:
    def __init__(self, mapping: dict):
        self._mapping = mapping
        self.closed = False
        self._next = 0
        self._last_url = None

    def goto(self, url: str, **kwargs):
        entry = self._mapping[url]
        if isinstance(entry, Exception):
            raise entry
        self._last_url = url
        if entry.get("navigate_to"):
            self._last_url = entry["navigate_to"]
        if entry.get("raise"):
            raise entry["raise"]
        return _FakeResp(entry.get("status", 200))

    def evaluate(self, expr, **kwargs):
        entry = self._mapping.get(self._last_url, {})
        return entry.get("body", "")

    def close(self):
        self.closed = True

    @property
    def url(self):
        return self._last_url


def test_page_link_status_classifies_render_results():
    page = _FakePage({
        "https://a.example.test/good": {"status": 200, "body": "Full article text here."},
        "https://a.example.test/redirect": {"status": 200, "body": "Loaded.", "navigate_to": "https://b.example.test/final"},
        "https://a.example.test/wall": {"status": 403, "body": "Access denied by Cloudflare. Just a moment…"},
        "https://a.example.test/denied": {"status": 403, "body": "Forbidden. nginx."},
        "https://a.example.test/boom": {"raise": RuntimeError("net::ERR_TIMED_OUT")},
    })
    out = _page_link_status(page, [
        "https://a.example.test/good",
        "https://a.example.test/redirect",
        "https://a.example.test/wall",
        "https://a.example.test/denied",
        "https://a.example.test/boom",
    ])
    assert out["https://a.example.test/good"]["status"] == "ok"
    assert out["https://a.example.test/redirect"]["final_url"] == "https://b.example.test/final"
    assert out["https://a.example.test/wall"]["status"] == "blocked"
    assert out["https://a.example.test/denied"]["status"] == "blocked"
    assert out["https://a.example.test/boom"] == {"status": "unknown", "status_code": None, "final_url": "https://a.example.test/boom"}


def test_browser_link_status_opens_throwaway_page_and_closes_it():
    class FakeCtx:
        def __init__(self):
            self.opened = False
        def new_page(self):
            self.opened = True
            return _FakePage({"https://a.example.test/x": {"status": 200, "body": "ok"}})

    ctx = FakeCtx()
    out = browser_link_status(ctx, ["https://a.example.test/x"])
    assert ctx.opened is True
    assert out["https://a.example.test/x"]["status"] == "ok"
