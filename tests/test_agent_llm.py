import json

from engine.agent_llm import AgentProvider, pending_jobs, answer_job, AGENT_JOBS_DIR
from engine.llm import get_provider


def test_unanswered_prompt_queues_job_and_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("engine.agent_llm.AGENT_JOBS_DIR", tmp_path)
    p = AgentProvider(tmp_path)
    out = p.complete("system x", "person y\ncontent z")
    assert out == "{}"
    jobs = pending_jobs(tmp_path)
    assert len(jobs) == 1
    assert jobs[0]["user"] == "person y\ncontent z"


def test_answered_prompt_returns_agent_response(tmp_path, monkeypatch):
    monkeypatch.setattr("engine.agent_llm.AGENT_JOBS_DIR", tmp_path)
    p = AgentProvider(tmp_path)
    p.complete("system x", "person y")  # queues the job
    job_id = json.loads(next(tmp_path.glob("*.job.json")).read_text())["id"]
    answer_job(job_id, '{"claims": [{"field": "position", "text": "Served as Head"}]}', tmp_path)
    out = p.complete("system x", "person y")
    assert out == '{"claims": [{"field": "position", "text": "Served as Head"}]}'
    assert pending_jobs(tmp_path) == []


def test_get_provider_selects_agent_via_env(monkeypatch):
    monkeypatch.setenv("WIKIMAKER_LLM", "agent")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from engine.llm import get_provider as gp
    from engine.agent_llm import AgentProvider
    assert isinstance(gp(), AgentProvider)
