from unittest.mock import patch

from engine.fetcher import check_liveness, get_wayback_url
from engine.models import Source, SourceReliability, VerificationState, PersonProfile, Claim
from wiki.draft import audit_profile, render_draft


def test_check_liveness_live():
    with patch("engine.fetcher.requests.get") as mock_get:
        resp = type("R", (), {"status_code": 200, "close": lambda self: None})()
        mock_get.return_value = resp
        assert check_liveness("https://example.test/a") == ("alive", None)


def test_check_liveness_dead_looks_up_wayback():
    with patch("engine.fetcher.requests.get") as mock_get, \
         patch("engine.fetcher.get_wayback_url", return_value="https://web.archive.org/web/2023id_/x"):
        resp = type("R", (), {"status_code": 404, "close": lambda self: None})()
        mock_get.return_value = resp
        assert check_liveness("https://example.test/gone") == ("dead", "https://web.archive.org/web/2023id_/x")


def test_check_liveness_blocked():
    with patch("engine.fetcher.requests.get") as mock_get:
        resp = type("R", (), {"status_code": 403, "close": lambda self: None})()
        mock_get.return_value = resp
        assert check_liveness("https://example.test/cloudflare") == ("blocked", None)


def test_get_wayback_url_parses_snapshot():
    with patch("engine.fetcher.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "archived_snapshots": {"closest": {"url": "https://web.archive.org/web/20230101/x"}}
        }
        assert get_wayback_url("https://example.test/x") == "https://web.archive.org/web/20230101/x"


def test_audit_excludes_dead_unarchived_source():
    source = Source(
        url="https://example.test/dead",
        title="Dead page",
        publisher="Example",
        reliability=SourceReliability.reliable_secondary,
        human_verified=True,
        liveness="dead",
        archive_url=None,
    )
    profile = PersonProfile(
        name="Example Person",
        sources=[source],
        claims=[Claim(
            field="known_for",
            text="Led an independently reported research project",
            source_url=source.url,
            verification=VerificationState.confirmed,
            draft_approved=True,
        )],
    )
    audit = audit_profile(profile)
    assert not audit.ready
    assert any(e.code == "source_url_dead" for e in audit.exclusions)


def test_renderer_cites_wayback_url_for_dead_archived_source():
    dead = Source(
        url="https://www.ndtv.com/india-news/example-1234567",
        title="Archived report",
        publisher="NDTV",
        reliability=SourceReliability.reliable_secondary,
        human_verified=True,
        liveness="dead",
        archive_url="https://web.archive.org/web/20230101/ndtv",
        date="2020",
    )
    second = Source(
        url="https://www.thehindu.com/example",
        title="Second coverage",
        publisher="The Hindu",
        reliability=SourceReliability.reliable_secondary,
        human_verified=True,
        liveness="alive",
    )
    profile = PersonProfile(
        name="Example Person",
        full_name="Dr. Example Person",
        nationality="Indian",
        sources=[dead, second],
        claims=[
            Claim(field="field", text="Animal biotechnology", source_url=dead.url,
                  verification=VerificationState.confirmed, draft_approved=True),
            Claim(field="known_for", text="Led an independently reported research project", source_url=dead.url,
                  verification=VerificationState.confirmed, draft_approved=True),
            Claim(field="position", text="Principal Scientist at an institute", source_url=second.url,
                  verification=VerificationState.confirmed, draft_approved=True),
        ],
    )
    wikitext = render_draft(profile)
    assert "https://web.archive.org/web/20230101/ndtv" in wikitext
    assert "archive-url=https://web.archive.org/web/20230101/ndtv" in wikitext
