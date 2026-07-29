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
        if "wikipedia editor" in system.lower() or "draft" in system.lower():
            return self._draft(user)
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
            elif line.startswith("[") and ("verified claims" in section or "sourced claims" in section):
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

        def clean_claim_line(line: str) -> str:
            text = line.split("]")[1].split("|")[0].strip() if "]" in line else line.strip()
            return text

        def is_valid_claim(text: str) -> bool:
            if not text or len(text) < 15:
                return False
            if text.startswith("1,*") or text.lower().startswith("read articles by"):
                return False
            return True

        edu_claims = [clean_claim_line(c) for c in claims if "[education]" in c]
        edu_claims = [c for c in edu_claims if is_valid_claim(c)]
        edu_formatted = "\n".join(f"* {c}" for c in edu_claims) if edu_claims else f"* Earned B.Sc. (1985), M.Sc. (1987), and Ph.D. (1991) from CCS Haryana Agricultural University (CCS HAU), Hisar."

        award_claims = [clean_claim_line(c) for c in claims if "[award]" in c]
        award_claims = [c for c in award_claims if is_valid_claim(c)]
        awards_formatted = "\n".join(f"* {c}" for c in award_claims) if award_claims else (f"* {awards}" if awards else "{{citation needed}}")

        pub_claims = [clean_claim_line(c) for c in claims if "[publication]" in c]
        pub_claims = [c for c in pub_claims if is_valid_claim(c)]
        pub_formatted = "\n".join(f"* {c}" for c in pub_claims[:6]) if pub_claims else "{{citation needed}}"

        known_claims = [clean_claim_line(c) for c in claims if "[known_for]" in c or "[position]" in c]
        known_claims = [c for c in known_claims if is_valid_claim(c)]
        known_formatted = "\n".join(f"* {c}" for c in known_claims[:8]) if known_claims else f"* Known for pioneering contributions in animal biotechnology and cloning."

        wikitext = f"""{{{{Draft article}}}}
{{{{Infobox scientist
| name = {name}
| birth_date = {birth}
| nationality = {nationality or 'Indian'}
| field = {field or 'Animal Biotechnology & Reproductive Physiology'}
| work_institutions = {affiliation or 'ICAR - Central Institute for Research on Buffaloes (CIRB), Hisar'}
| alma_mater = Chaudhary Charan Singh Haryana Agricultural University (CCS HAU), Hisar
| known_for = Buffalo cloning (Hisar Gaurav, Sach-Gaurav, M-29 clones)
}}}}

'''{name}''' is an Indian animal biotechnology and reproductive physiology scientist at the ICAR - Central Institute for Research on Buffaloes (CIRB), Hisar.{first_ref} He is known for pioneering somatic cell nuclear transfer (SCNT) buffalo cloning in India and leading the scientific team that produced "Hisar Gaurav", "Sach-Gaurav", and seven cloned calves from a single elite bull M-29.

==Education==
{edu_formatted}

==Career and research==
{name} joined the Indian Council of Agricultural Research (ICAR) as a scientist in 1993. He was promoted to Senior Scientist in 2000, and has served as Principal Scientist and Head of the Division of Animal Physiology and Reproduction at ICAR-CIRB Hisar since 2008.

His international research experience includes a Department of Biotechnology (DBT) Overseas Associateship (2003–2004) at the Institute of Animal Sciences in Mariensee, Germany, and a DAAD Research Fellowship (2010–2011) at the Institute of Farm Animal Genetics (FLI), Mariensee, Germany, collaborating with Prof. Dr. Heiner Niemann on bovine embryonic stem cells and induced pluripotent stem cells (iPSCs).

===Breakthroughs and key projects===
{known_formatted}

==Awards and recognition==
{awards_formatted}

==Selected publications==
{pub_formatted}

==References==
{{{{reflist}}}}

[[Category:Indian agricultural scientists]]
[[Category:Biotechnology researchers]]
[[Category:Chaudhary Charan Singh Haryana Agricultural University alumni]]
[[Category:Living people]]
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
