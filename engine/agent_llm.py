"""Agent-as-LLM bridge: no API key required — the coding agent answers the prompts.

The provider turns every extraction/classification prompt into a deterministic job
file in `agent_jobs/` (keyed by a hash of the prompt). A human or coding agent reads
the job, reads the source themselves, and writes back a `.response.json` containing
the JSON the caller expected. Re-running the same prompt then returns the answer.
Set WIKIMAKER_LLM=agent to select this provider.

Unlike the stub, this never fabricates: an unanswered job simply yields `{}` (no
claims, no classification), and the agent's answer is applied only when written.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .llm import LLMProvider

AGENT_JOBS_DIR = Path(__file__).resolve().parents[1] / "agent_jobs"


def _job_id(system: str, user: str) -> str:
    return hashlib.sha1((system + "\n" + user).encode()).hexdigest()[:16]


class AgentProvider(LLMProvider):
    """Writes a prompt as a job; returns a previously written agent answer if any."""

    def __init__(self, jobs_dir: Path = AGENT_JOBS_DIR):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(exist_ok=True, parents=True)

    def complete(self, system: str, user: str) -> str:
        job_id = _job_id(system, user)
        job_path = self.jobs_dir / f"{job_id}.job.json"
        resp_path = self.jobs_dir / f"{job_id}.response.json"
        if resp_path.exists():
            return json.loads(resp_path.read_text())["response"]
        if not job_path.exists():
            job_path.write_text(json.dumps(
                {"id": job_id, "system": system, "user": user}, indent=2, ensure_ascii=False
            ))
        return "{}"


def pending_jobs(jobs_dir: Path = AGENT_JOBS_DIR) -> list[dict]:
    """Agent jobs that have been queued but not yet answered."""
    jobs = []
    for job_path in sorted(Path(jobs_dir).glob("*.job.json")):
        resp_path = job_path.with_name(job_path.name.replace(".job.json", ".response.json"))
        if resp_path.exists():
            continue
        try:
            jobs.append(json.loads(job_path.read_text()))
        except Exception:
            continue
    return jobs


def answer_job(job_id: str, response: str, jobs_dir: Path = AGENT_JOBS_DIR) -> Path:
    """Record an agent's answer for a job so a re-run of the prompt returns it."""
    resp_path = Path(jobs_dir) / f"{job_id}.response.json"
    resp_path.write_text(json.dumps({"id": job_id, "response": response}, ensure_ascii=False))
    return resp_path
