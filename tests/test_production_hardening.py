"""Production hardening unit tests for SSRF guards, atomic persistence, and citation safety."""
import json

from engine.fetcher import is_safe_public_url, _direct_fetch, check_liveness
from engine.models import PersonProfile, Source, SourceReliability
from wiki.draft import _cite_value, _citation
import backend.store as store


def test_is_safe_public_url_blocks_private_and_loopback():
    assert not is_safe_public_url("http://127.0.0.1:8000/secret")
    assert not is_safe_public_url("http://localhost:3890/api")
    assert not is_safe_public_url("http://169.254.169.254/latest/meta-data")
    assert not is_safe_public_url("http://10.0.0.1/admin")
    assert not is_safe_public_url("http://192.168.1.1/router")
    assert not is_safe_public_url("ftp://example.com/file")
    assert not is_safe_public_url("javascript:alert(1)")


def test_is_safe_public_url_allows_public_https():
    assert is_safe_public_url("https://www.nature.com/articles/s41598-019-47909-8")
    assert is_safe_public_url("https://en.wikipedia.org/wiki/Main_Page")


def test_fetch_url_and_liveness_reject_unsafe_urls():
    assert check_liveness("http://127.0.0.1:3890/test") == ("unknown", None)
    assert check_liveness("http://169.254.169.254/metadata") == ("unknown", None)
    assert _direct_fetch("http://localhost:9000/dump") is None


def test_atomic_session_save(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    sid = "py-hardening-test-1234"
    profile = PersonProfile(
        name="Hardening Test Subject",
        session_id=sid,
    )
    store._sessions[sid] = profile
    store._wiki_statuses[sid] = {"status": "clear"}

    store._save_session(sid)

    target_file = tmp_path / f"{sid}.json"
    assert target_file.exists()
    data = json.loads(target_file.read_text(encoding="utf-8"))
    assert data["profile"]["name"] == "Hardening Test Subject"
    assert data["profile"]["session_id"] == sid

    # Verify no dangling temp files remain in directory
    temp_files = list(tmp_path.glob("*.tmp"))
    assert len(temp_files) == 0


def test_cite_value_escapes_wikitext_template_braces():
    raw_title = "Study on {{CRISPR/Cas9}} in Buffaloes | Nature {{2023}}"
    escaped = _cite_value(raw_title)
    assert "{{CRISPR" not in escaped
    assert "2023}}" not in escaped
    assert "|" not in escaped
    assert "&#123;&#123;CRISPR/Cas9&#125;&#125;" in escaped
    assert "&#123;&#123;2023&#125;&#125;" in escaped
    assert "{{!}}" in escaped


def test_citation_with_curly_braces():
    source = Source(
        url="https://doi.org/10.1089/cell.2023.0003",
        title="Gene Editing {{CRISPR}} Study",
        publisher="Cellular Reprogramming",
        reliability=SourceReliability.reliable_secondary,
    )
    used = set()
    rendered = _citation(source, used)
    assert "{{cite web" in rendered
    assert "&#123;&#123;CRISPR&#125;&#125;" in rendered
