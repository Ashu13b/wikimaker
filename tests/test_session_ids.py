"""Tests for stable subject/session ids — same-named people cannot collide."""
import json

from engine.models import PersonProfile
from backend import store
from backend.main import ResearchRequest, research_start


def _profile(name: str, session_id: str, wikidata_id: str | None = None) -> PersonProfile:
    return PersonProfile(name=name, session_id=session_id, wikidata_id=wikidata_id)


def test_new_session_ids_are_unique_per_name_duplicate():
    ids = {store._new_session_id("Prem Singh Yadav") for _ in range(50)}
    assert len(ids) == 50
    assert all(i.startswith("py-prem-singh-yadav-") for i in ids)


def test_resolve_profile_by_id_and_by_name(monkeypatch):
    a = _profile("Prem Singh Yadav", "py-prem-singh-yadav-aaaa")
    b = _profile("Prem Singh Yadav", "py-prem-singh-yadav-bbbb")
    c = _profile("Other Person", "py-other-person-cccc")
    monkeypatch.setattr(store, "_sessions", {a.session_id: a, b.session_id: b, c.session_id: c})

    assert store._resolve_profile("py-prem-singh-yadav-bbbb") is b
    assert store._resolve_profile("Other Person") is c
    assert store._resolve_profile("No Such Person") is None


def test_same_name_with_distinct_ids_is_ambiguous(monkeypatch):
    a = _profile("Prem Singh Yadav", "py-prem-singh-yadav-aaaa")
    b = _profile("Prem Singh Yadav", "py-prem-singh-yadav-bbbb")
    monkeypatch.setattr(store, "_sessions", {a.session_id: a, b.session_id: b})

    try:
        store._get_profile("Prem Singh Yadav")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    else:
        raise AssertionError("expected 409 for ambiguous name")


def test_save_writes_id_file_and_keys_by_id(tmp_path, monkeypatch):
    profile = _profile("Example Person", "py-example-person-fixed")
    sid = profile.session_id or store._new_session_id(profile.name)
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {sid: profile})
    monkeypatch.setattr(store, "_wiki_statuses", {sid: {"status": "clear"}})

    store._save_session(sid)

    assert (tmp_path / "py-example-person-fixed.json").exists()
    assert store._sessions[sid] is profile
    assert not (tmp_path / "Example_Person.json").exists()


def test_legacy_session_without_id_migrates_on_save(tmp_path, monkeypatch):
    profile = PersonProfile(name="Legacy Person")
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {"Legacy Person": profile})
    monkeypatch.setattr(store, "_wiki_statuses", {})

    store._save_session("Legacy Person")

    assert profile.session_id is not None
    assert profile.session_id in store._sessions
    assert (tmp_path / f"{profile.session_id}.json").exists()


def test_identity_matches_policy():
    assert store._identity_matches({"name": "A B", "wikidata_id": "Q1"}, "A B", "Q1") is True
    assert store._identity_matches({"name": "A B", "wikidata_id": None}, "A B", None) is True
    assert store._identity_matches({"name": "A B", "wikidata_id": "Q1"}, "A B", "Q2") is False
    assert store._identity_matches({"name": "A B", "wikidata_id": "Q1"}, "A B", None) is False
    assert store._identity_matches({"name": "A B", "wikidata_id": "Q1"}, "A C", "Q1") is False


def test_resume_migrates_legacy_file_to_id_file(tmp_path, monkeypatch):
    profile = PersonProfile(name="Legacy Person", field="Science")
    payload = {
        "profile": json.loads(profile.model_dump_json()),
        "wiki_status": {"status": "clear", "url": None, "note": None},
    }
    legacy = tmp_path / "Legacy_Person.json"
    legacy.write_text(json.dumps(payload))
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})

    class _Clear:
        def model_dump(self):
            return {"status": "clear", "url": None, "note": None}

    monkeypatch.setattr("wiki.wiki_check.check_existing_page", lambda title: _Clear())

    from backend.routes_sessions import resume_session
    result = resume_session({"file": "Legacy_Person.json"})

    sid = result["profile"]["session_id"]
    assert sid is not None
    assert (tmp_path / f"{sid}.json").exists()
    assert not legacy.exists()
    assert store._sessions[sid].name == "Legacy Person"


def test_resume_refreshes_wiki_status_instead_of_trusting_stored(monkeypatch, tmp_path):
    from backend import store as st
    profile = PersonProfile(name="Legacy Person")
    payload = {
        "profile": json.loads(profile.model_dump_json()),
        "wiki_status": {"status": "clear", "url": None, "note": None},
    }
    legacy = tmp_path / "Legacy_Person.json"
    legacy.write_text(json.dumps(payload))
    monkeypatch.setattr(st, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(st, "_sessions", {})
    monkeypatch.setattr(st, "_wiki_statuses", {})

    class _Exists:
        def model_dump(self):
            return {"status": "exists", "url": "https://en.wikipedia.org/wiki/Legacy_Person", "note": "A Wikipedia article already exists for this person."}

    monkeypatch.setattr("wiki.wiki_check.check_existing_page", lambda title: _Exists())

    from backend.routes_sessions import resume_session
    result = resume_session({"file": "Legacy_Person.json"})

    assert result["wiki_status"]["status"] == "exists"


def test_research_start_resumes_in_memory_same_identity(monkeypatch):
    existing = _profile("Same Name", "py-same-name-aaaa")
    monkeypatch.setattr(store, "_sessions", {existing.session_id: existing})
    monkeypatch.setattr(store, "_wiki_statuses", {existing.session_id: {"status": "clear", "url": None, "note": None}})
    monkeypatch.setattr(store, "_find_session_on_disk", lambda pred: None)

    result = research_start(ResearchRequest(name="Same Name"))

    assert result["resumed"] is True
    assert result["profile"]["session_id"] == "py-same-name-aaaa"


def test_research_start_resumes_same_name_different_identity_creates_new(monkeypatch):
    existing = _profile("Same Name", "py-same-name-aaaa", wikidata_id="Q1")
    monkeypatch.setattr(store, "_sessions", {existing.session_id: existing})
    monkeypatch.setattr(store, "_wiki_statuses", {existing.session_id: {"status": "clear", "url": None, "note": None}})
    _mock_fresh_research_pipeline(monkeypatch)
    # Same name, different/absent wikidata -> distinct person -> must NOT resume.
    result = research_start(ResearchRequest(name="Same Name", wikidata_id="Q2"))

    assert result["resumed"] is False
    assert result["profile"]["session_id"] != "py-same-name-aaaa"


def _mock_fresh_research_pipeline(monkeypatch):
    class _WikiStatus:
        def model_dump(self):
            return {"status": "clear", "url": None, "note": None}

    monkeypatch.setattr("backend.routes_research.check_existing_page", lambda name: _WikiStatus())
    monkeypatch.setattr("backend.routes_research.fetch_auto_sources", lambda *a, **k: ([], None))
    monkeypatch.setattr("backend.routes_research.fetch_institution_sources", lambda *a, **k: [])


def test_research_start_migrates_legacy_session_from_disk(tmp_path, monkeypatch):
    profile = PersonProfile(name="Legacy Person")
    payload = {
        "profile": json.loads(profile.model_dump_json()),
        "wiki_status": {"status": "clear", "url": None, "note": None},
    }
    legacy = tmp_path / "Legacy_Person.json"
    legacy.write_text(json.dumps(payload))
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})

    result = research_start(ResearchRequest(name="Legacy Person"))

    assert result["resumed"] is True
    sid = result["profile"]["session_id"]
    assert sid is not None
    assert not legacy.exists()
    assert (tmp_path / f"{sid}.json").exists()


def test_delete_only_evicts_target_not_same_named_namesake(tmp_path, monkeypatch):
    a = _profile("Same Name", "py-same-aaaa")
    b = _profile("Same Name", "py-same-bbbb")
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {a.session_id: a, b.session_id: b})
    monkeypatch.setattr(store, "_wiki_statuses", {a.session_id: {"status": "clear"}, b.session_id: {"status": "clear"}})
    (tmp_path / "py-same-aaaa.json").write_text("{}")
    (tmp_path / "py-same-bbbb.json").write_text("{}")
    from backend.main import delete_session

    delete_session("py-same-aaaa")

    assert a.session_id not in store._sessions
    assert store._sessions.get(b.session_id or "") is b


def test_corrupt_legacy_file_is_skipped_and_fresh_session_created(tmp_path, monkeypatch):
    (tmp_path / "Corrupt_Person.json").write_text("{not valid json")
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})
    _mock_fresh_research_pipeline(monkeypatch)

    result = research_start(ResearchRequest(name="Corrupt Person"))

    assert result["resumed"] is False
    assert result["profile"]["session_id"] is not None


def test_legacy_filename_with_id_keyed_content_migrates_keeping_session_id(tmp_path, monkeypatch):
    profile = PersonProfile(name="Legacy Person", session_id="py-legacy-person-abcd1234")
    payload = {
        "profile": json.loads(profile.model_dump_json()),
        "wiki_status": {"status": "clear", "url": None, "note": None},
    }
    legacy = tmp_path / "Legacy_Person.json"
    legacy.write_text(json.dumps(payload))
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})

    class _Clear:
        def model_dump(self):
            return {"status": "clear", "url": None, "note": None}

    monkeypatch.setattr("wiki.wiki_check.check_existing_page", lambda title: _Clear())

    from backend.routes_sessions import resume_session
    result = resume_session({"file": "Legacy_Person.json"})

    sid = result["profile"]["session_id"]
    assert sid == "py-legacy-person-abcd1234"
    assert (tmp_path / f"{sid}.json").exists()
    assert not legacy.exists()
