from __future__ import annotations
import os
import sys
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class ClaudeProvider:
    def __init__(self) -> None:
        import anthropic
        self._client = anthropic.Anthropic()
        self._model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

    def complete(self, system: str, user: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text  # type: ignore[index]


class GeminiProvider:
    def __init__(self) -> None:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        self._model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=None,  # injected per-call
        )
        self._genai = genai

    def complete(self, system: str, user: str) -> str:
        model = self._genai.GenerativeModel(
            model_name=self._model.model_name,
            system_instruction=system,
        )
        resp = model.generate_content(user)
        return resp.text


class VertexClaudeProvider:
    """Claude via Google Vertex AI (application-default credentials).

    Used when ANTHROPIC_VERTEX_PROJECT_ID is set and no ANTHROPIC_API_KEY is.
    The constructor probes the model so a project without model access falls
    back cleanly to the stub instead of failing on the first real call.
    """

    def __init__(self) -> None:
        import anthropic
        self._client = anthropic.AnthropicVertex(
            project_id=os.environ["ANTHROPIC_VERTEX_PROJECT_ID"],
            region=os.environ.get("CLOUD_ML_REGION", "us-east5"),
        )
        self._model = os.environ.get("VERTEX_CLAUDE_MODEL", "claude-sonnet-4-5@20250929")
        self._client.messages.create(
            model=self._model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )

    def complete(self, system: str, user: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text  # type: ignore[index]


class LocalProvider:
    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError("Local provider not yet wired — set WIKIMAKER_LLM=claude")


class NullProvider:
    """Fallback when no API key is configured — LLM-dependent steps silently skip."""
    def complete(self, system: str, user: str) -> str:
        return "{}"


class StubProvider:
    """Rule-based stub — produces plausible output for all call types without an LLM.
    Replace with a real provider by setting ANTHROPIC_API_KEY + WIKIMAKER_LLM=claude."""

    def complete(self, system: str, user: str) -> str:
        import json
        if "wikipedia editor" in system.lower() or "draft" in system.lower():
            raise NotImplementedError(
                "The stub provider cannot draft articles. Drafting is deterministic "
                "and server-owned: use wiki.draft.render_draft, or configure an LLM "
                "API key for research steps only."
            )
        if "reliability" in system:
            return self._classify(user)
        if "claims" in system.lower():
            return self._extract(user)
        return "{}"

    # ── classifier ────────────────────────────────────────────────────────────

    def _classify(self, user: str) -> str:
        import json
        url = ""
        for line in user.splitlines():
            if line.startswith("URL:"):
                url = line.split(":", 1)[1].strip().lower()
                break
        if any(kw in url for kw in ["ncbi", "pubmed", "doi.org", "plos", "springer"]):
            return json.dumps({"reliability": "reliable_secondary", "reason": "academic publisher"})
        if any(kw in url for kw in ["researchgate", "academia.edu", "linkedin"]):
            return json.dumps({"reliability": "self_published", "reason": "self-published profile"})
        return json.dumps({"reliability": "primary", "reason": "stub classification"})

    # ── extractor ─────────────────────────────────────────────────────────────

    def _extract(self, user: str) -> str:
        import json, re
        person, content, title, publisher = "", "", "", ""
        for line in user.splitlines():
            if line.startswith("Person:"):
                person = line.split(":", 1)[1].strip()
            elif line.startswith("Content:"):
                content = line.split(":", 1)[1].strip()
            elif line.startswith("Title:"):
                title = line.split(":", 1)[1].strip()
            elif line.startswith("Publisher:"):
                publisher = line.split(":", 1)[1].strip()

        if not person:
            return json.dumps({"claims": []})

        name_parts = {p.lower() for p in person.split() if len(p) > 2}

        _FIELD_KEYWORDS: list[tuple[list[str], str]] = [
            (["born", "birth"], "birth_date"),
            (["award", "prize", "fellow", "honour", "felicitat"], "award"),
            (["phd", "m.sc", "b.sc", "degree", "studied", "graduated"], "education"),
            (["director", "principal scientist", "head", "chief", "professor", "scientist"], "position"),
            (["published", "paper", "journal", "article", "research"], "publication"),
            (["university", "institute", "icar", "iit", "college", "laborator"], "affiliation"),
        ]

        _PRONOUNS = {"he", "she", "they", "his", "her", "their", "who"}

        claims = []

        # Treat title as a publication claim when content doesn't mention the person
        content_lower = content.lower()
        person_mentioned_in_content = (
            any(p in content_lower for p in name_parts)
            or (content_lower.split()[:1] or [""])[0] in _PRONOUNS
        )
        paper_keywords = ["gene", "embryo", "protein", "effect", "analysis", "study",
                          "assessment", "evaluation", "production", "role", "impact",
                          "crispr", "sperm", "oocyte", "buffalo", "bovine", "cloning"]
        effective_title = title or content
        if (
            effective_title
            and not person_mentioned_in_content
            and any(kw in effective_title.lower() for kw in paper_keywords)
        ):
            pub_text = f'{person} co-authored "{effective_title}"'
            if publisher:
                pub_text += f', published in {publisher}'
            claims.append({"field": "publication", "text": pub_text})
            return json.dumps({"claims": claims})

        sentences = [s.strip() for s in re.split(r'[.!?]', content) if len(s.strip()) > 15]
        for sent in sentences:
            sl = sent.lower()
            first_word = sl.split()[0] if sl.split() else ""
            mentions_person = any(p in sl for p in name_parts) or first_word in _PRONOUNS or len(sentences) <= 3
            if not mentions_person:
                continue
            field = "known_for"
            for keywords, f in _FIELD_KEYWORDS:
                if any(kw in sl for kw in keywords):
                    field = f
                    break
            if field == "birth_date":
                animal_kws = ["cloned", "cloning", "animal", "buffalo", "calf", "cow", "bull", "sheep", "goat", "offspring", "garima", "samrupa", "ganga", "dolly"]
                if any(akw in sl for akw in animal_kws):
                    field = "known_for"
            claims.append({"field": field, "text": sent.strip()})
            if len(claims) >= 3:
                break

        return json.dumps({"claims": claims})


_stub_warned = False
_agent_warned = False


def _agent_provider() -> "AgentProvider":
    from .agent_llm import AgentProvider
    return AgentProvider()


def _warn_agent_mode() -> None:
    global _agent_warned
    if not _agent_warned:
        _agent_warned = True
        print(
            "WIKIMAKER: no LLM API key, routing intelligence to the coding agent. "
            "Extraction/classification prompts are queued in agent_jobs/ — answer them "
            "and re-run to apply. (WIKIMAKER_LLM=agent to force; =stub to disable.)",
            file=sys.stderr,
        )


def has_real_llm() -> bool:
    """True when an API-backed provider is configured, not a stub/null/local fallback."""
    return not isinstance(get_provider(), (StubProvider, NullProvider, LocalProvider))


def _stub_provider() -> StubProvider:
    global _stub_warned
    if not _stub_warned:
        _stub_warned = True
        print(
            "WARNING: No LLM API key configured; falling back to rule-based StubProvider. "
            "Research classification/extraction will be low quality and article drafting is "
            "unavailable. Set ANTHROPIC_API_KEY (WIKIMAKER_LLM=claude) or GEMINI_API_KEY.",
            file=sys.stderr,
        )
    return StubProvider()


def get_provider() -> LLMProvider:
    backend = os.environ.get("WIKIMAKER_LLM", "claude")
    if backend == "claude":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            # Try reading from ~/.anthropic/credentials or other SDK locations
            try:
                import anthropic
                c = anthropic.Anthropic()
                # SDK stores the resolved key as an attribute
                key = getattr(c, "api_key", "") or ""
            except Exception:
                pass
        if key:
            try:
                return ClaudeProvider()
            except Exception:
                pass
        if os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID"):
            try:
                return VertexClaudeProvider()
            except Exception:
                pass
        _warn_agent_mode()
        return _agent_provider()
    if backend == "gemini":
        if os.environ.get("GEMINI_API_KEY"):
            try:
                return GeminiProvider()
            except Exception:
                pass
        _warn_agent_mode()
        return _agent_provider()
    if backend == "local":
        return LocalProvider()
    if backend == "agent":
        return _agent_provider()
    if backend == "stub":
        return _stub_provider()
    raise ValueError(f"Unknown WIKIMAKER_LLM value: {backend}")
