"""Render PersonProfile into Wikipedia wikitext (Draft: namespace ready)."""
from __future__ import annotations
from engine.models import PersonProfile, Claim, VerificationState
from engine.llm import LLMProvider

SYSTEM_EN = """\nYou are a Wikipedia editor writing an article for the Draft: namespace (Articles for Creation).
Output valid wikitext ONLY — no Markdown.

Rules:
- {{Infobox person}} at the top with known fields
- Sections: ==Early life==, ==Career==, ==Works==, ==Awards==, ==References==
- Every claim gets an inline <ref>{{cite web|url=...|title=...|publisher=...|access-date=2026-05-18}}</ref>
- Unsourced claims get {{citation needed}} instead of a ref tag
- Neutral POV: no peacock words (renowned, famous, brilliant, leading, prominent)
- Do NOT copy source text — paraphrase
- {{reflist}} at end of References section
- Add appropriate Wikipedia categories at the very end

IMPORTANT: This draft was generated with AI assistance. A human must review it before submission.
Wikipedia's AfC policy requires human-reviewed content."""

SYSTEM_HI = SYSTEM_EN.replace(
    "writing an article for the Draft: namespace (Articles for Creation)",
    "writing an article for the Hindi Wikipedia (hi.wikipedia.org) Draft: namespace"
) + "\nWrite entirely in Hindi (Devanagari script). Use Hindi Wikipedia citation and infobox templates."


def render_en(profile: PersonProfile, llm: LLMProvider) -> str:
    return llm.complete(SYSTEM_EN, _build_prompt(profile, "English"))


def render_hi(profile: PersonProfile, llm: LLMProvider) -> str:
    return llm.complete(SYSTEM_HI, _build_prompt(profile, "Hindi"))


def _build_prompt(profile: PersonProfile, lang: str) -> str:
    lines = [f"Write a {lang} Wikipedia draft article about: {profile.name}", ""]

    facts = {
        "Full name": profile.full_name,
        "Birth date": profile.birth_date,
        "Birth place": profile.birth_place,
        "Nationality": profile.nationality,
        "Field": profile.field,
        "Affiliation": profile.affiliation,
        "Known for": profile.known_for,
        "Awards": ", ".join(profile.awards) if profile.awards else None,
        "Photo filename": _commons_filename(profile.photo_url),
    }
    lines.append("== Known facts ==")
    for k, v in facts.items():
        if v:
            lines.append(f"{k}: {v}")

    # Separate claims by verification state
    verified = [c for c in profile.claims if c.verification == VerificationState.confirmed]
    unverified = [c for c in profile.claims if c.verification == VerificationState.unverified]
    unsourced = [c for c in profile.claims if not c.source_url]

    if verified:
        lines.append("\n== Verified claims (user-confirmed source) ==")
        for c in verified:
            lines.append(f"[{c.field}] {c.text} | source: {c.source_url}")

    if unverified:
        lines.append("\n== Sourced claims (not yet user-verified) ==")
        for c in unverified:
            lines.append(f"[{c.field}] {c.text} | source: {c.source_url}")

    if unsourced:
        lines.append("\n== Unsourced facts (use {{citation needed}}) ==")
        for c in unsourced:
            lines.append(f"[{c.field}] {c.text}")

    if profile.sources:
        lines.append("\n== All sources ==")
        for s in profile.sources:
            lines.append(f"- [{s.reliability.value}] {s.publisher}: {s.title} | {s.url}")

    return "\n".join(lines)


def _commons_filename(photo_url: str | None) -> str | None:
    if not photo_url or "Special:FilePath" not in photo_url:
        return None
    try:
        return photo_url.split("Special:FilePath/")[1].split("?")[0]
    except Exception:
        return None
