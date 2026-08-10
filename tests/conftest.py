"""Isolate every test's session store from the real sessions/ directory."""
import pytest

from backend import store


@pytest.fixture(autouse=True)
def _isolated_sessions(tmp_path, monkeypatch):
    isolated = tmp_path / "sessions"
    isolated.mkdir(exist_ok=True)
    monkeypatch.setattr(store, "SESSIONS_DIR", isolated)
    yield
