from __future__ import annotations
import os
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
        import json, re
        if "reliability" in system:
            return self._classify(user)
        if "claims" in system.lower():
            return self._extract(user)
        if "wikipedia editor" in system.lower():
            return self._draft(user)
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

        sentences = [s.strip() for s in re.split(r'[.!?]', content) if len(s.strip()) > 20]
        for sent in sentences:
            sl = sent.lower()
            first_word = sl.split()[0] if sl.split() else ""
            mentions_person = any(p in sl for p in name_parts) or first_word in _PRONOUNS
            if not mentions_person:
                continue
            field = "known_for"
            for keywords, f in _FIELD_KEYWORDS:
                if any(kw in sl for kw in keywords):
                    field = f
                    break
            claims.append({"field": field, "text": sent.strip()})
            if len(claims) >= 3:
                break

        return json.dumps({"claims": claims})

    # ── drafter ───────────────────────────────────────────────────────────────

    def _draft(self, user: str) -> str:
        lines = user.splitlines()
        facts: dict[str, str] = {}
        claims: list[str] = []
        sources: list[str] = []
        section = ""

        for line in lines:
            if line.startswith("== "):
                section = line.strip("= ").lower()
                continue
            if ":" in line and section == "known facts":
                k, _, v = line.partition(":")
                facts[k.strip().lower()] = v.strip()
            elif line.startswith("[") and "source:" in line and "claims" in section:
                claims.append(line.strip())
            elif line.startswith("- [") and section == "all sources":
                sources.append(line.strip())

        name = facts.get("full name") or (lines[0].split("about:")[-1].strip() if lines else "Unknown")
        birth = facts.get("birth date", "")
        nationality = facts.get("nationality", "")
        field = facts.get("field", "")
        affiliation = facts.get("affiliation", "")
        known_for = facts.get("known for", "")
        awards = facts.get("awards", "")

        ref_lines = []
        for i, src in enumerate(sources[:10], 1):
            # - [reliable_secondary] Publisher: Title | URL
            parts = src.lstrip("- ").split("|")
            url = parts[-1].strip() if len(parts) > 1 else ""
            meta = parts[0] if parts else src
            title_part = meta.split("]", 1)[-1].strip()
            publisher = title_part.split(":", 1)[0].strip() if ":" in title_part else ""
            title = title_part.split(":", 1)[1].strip() if ":" in title_part else title_part
            ref_lines.append(f'<ref>{{{{cite web|url={url}|title={title}|publisher={publisher}|access-date=2026-05-18}}}}</ref>')

        refs = ref_lines[:3]  # use first 3 refs inline
        first_ref = refs[0] if refs else "{{citation needed}}"

        wikitext = f"""{{{{Draft article}}}}
{{{{Infobox person
| name = {name}
| birth_date = {birth}
| nationality = {nationality}
| occupation = {field}
| employer = {affiliation}
}}}}

'''{name}''' is a {nationality + ' ' if nationality else ''}{field.lower() if field else 'researcher'}{(' at ' + affiliation) if affiliation else ''}.{first_ref}

==Early life==
{name} was born{(' on ' + birth) if birth else ''}.{{{{citation needed}}}}

==Career==
{name} is known for {known_for or ('work in ' + field.lower() if field else 'contributions to the field')}.{first_ref}
{chr(10).join(f'* {c.split("|")[0].strip()}' for c in claims[:5])}

==Awards and recognition==
{('* ' + awards) if awards else '{{citation needed}}'}

==References==
{{{{reflist}}}}

{''.join(f'[[Category:{c}]]' for c in [nationality + ' scientists' if nationality else '', field] if c)}
"""
        return wikitext.strip()


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
        return StubProvider()
    if backend == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            return StubProvider()
        try:
            return GeminiProvider()
        except Exception:
            return StubProvider()
    if backend == "local":
        return LocalProvider()
    raise ValueError(f"Unknown WIKIMAKER_LLM value: {backend}")
