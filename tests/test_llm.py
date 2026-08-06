from engine.llm import StubProvider, VertexClaudeProvider, get_provider
from engine.extractor import extract_claims
from engine.models import PersonProfile, Source, SourceReliability


def test_extract_claims_is_noop_under_stub():
    profile = PersonProfile(name="Example Person")
    src = Source(
        url="https://example.test/news",
        title="Example news",
        publisher="Example News",
        reliability=SourceReliability.reliable_secondary,
        snippet="Example Person won an award in 2020.",
    )
    assert extract_claims(profile, [src], StubProvider()) == []


def test_get_provider_uses_vertex_when_available(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "proj")
    monkeypatch.setenv("CLOUD_ML_REGION", "us-east5")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import anthropic

    class _Resp:
        content = [type("C", (), {"text": "ok"})()]

    class _Messages:
        @staticmethod
        def create(*a, **k):
            return _Resp()

    class _FakeVertex:
        def __init__(self, project_id, region):
            self.messages = _Messages()

    monkeypatch.setattr(anthropic, "AnthropicVertex", _FakeVertex)
    assert isinstance(get_provider(), VertexClaudeProvider)


def test_get_provider_falls_back_to_agent_when_vertex_unavailable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "proj")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import anthropic

    class _BrokenVertex:
        def __init__(self, project_id, region):
            self.messages = type(
                "M", (), {"create": staticmethod(lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model")))}
            )()

    monkeypatch.setattr(anthropic, "AnthropicVertex", _BrokenVertex)
    from engine.agent_llm import AgentProvider
    assert isinstance(get_provider(), AgentProvider)
