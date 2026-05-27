"""Extract structured claims from sources, each bound to a citation URL."""
from __future__ import annotations
import json
from .models import Source, Claim, PersonProfile, SourceReliability, VerificationState
from .llm import LLMProvider

# The Wikipedia slots we expect a sourced value for (publication handled separately)
WIKI_SLOTS = [
    "full_name", "birth_date", "birth_place", "nationality",
    "affiliation", "position", "field", "education", "known_for", "award",
]

# What kind of source typically fills each slot
SLOT_SOURCE_HINTS: dict[str, str] = {
    "birth_date":   "news article, obituary, or institutional bio",
    "birth_place":  "news article or institutional bio",
    "nationality":  "institutional bio or news",
    "affiliation":  "institution website (faculty/staff page)",
    "position":     "institution website (faculty/staff page)",
    "field":        "institution website or research profile",
    "education":    "institution website or CV/bio page",
    "known_for":    "news article or research profile",
    "award":        "press release, news, or institution website",
    "full_name":    "institution website or official document",
}


def find_missing_slots(profile: PersonProfile, claims: list[Claim]) -> list[str]:
    """Return WIKI_SLOTS not covered by any claim or profile-level field."""
    filled: set[str] = {c.field for c in claims}
    # User-entered form data counts as filled (unsourced but known)
    if profile.birth_date:  filled.add("birth_date")
    if profile.birth_place: filled.add("birth_place")
    if profile.nationality: filled.add("nationality")
    if profile.affiliation: filled.add("affiliation")
    if profile.field:       filled.add("field")
    if profile.full_name:   filled.add("full_name")
    return [s for s in WIKI_SLOTS if s not in filled]

SYSTEM = """\
Extract structured facts about a person from a source for a Wikipedia article.
Return only verifiable facts stated in the source. No speculation or inference.
Use neutral language — no "renowned", "famous", "brilliant", "leading".

Return JSON: {"claims": [{"field": "...", "text": "...", "date_context": "..."}]}

Valid fields: full_name, birth_date, birth_place, death_date, nationality,
field, affiliation, education, position, known_for, award, publication.

Field definitions (be strict):
- birth_date: the PERSON's own date or year of birth — NOT birth of an animal, technology, institution, or idea mentioned in the source
- birth_place: the PERSON's own birthplace — not a location in a paper title or abstract
- publication: a paper or book authored BY this person — not a citation or reference to others' work
- award: an honour received BY this person — not an award mentioned in passing
Only extract a field if the source clearly states it about this specific person.

date_context rules (critical):
- Only set date_context if a year or date range appears VERBATIM in the source text for that claim.
- Valid examples: "2005", "2005–2015", "since 2020", "1990s", "July 2008"
- If no year is explicitly stated for this fact in the source, omit date_context entirely.
- NEVER infer or guess a date from context. "received the award" → no date_context."""


def extract_claims(profile: PersonProfile, sources: list[Source], llm: LLMProvider) -> list[Claim]:
    all_claims: list[Claim] = []

    # prioritise RS sources, then process all with a source
    ordered = sorted(sources, key=lambda s: s.reliability != SourceReliability.reliable_secondary)

    for source in ordered[:8]:  # cap to avoid token overrun
        # Skip sources flagged as the wrong person
        if source.relevance_flag == "likely_wrong":
            continue

        # Build content block: prefer snippet; fall back to title as surrogate
        content = source.snippet or ""
        title = source.title if source.title and source.title != source.url else ""
        if not content and not title:
            continue

        # If snippet is too thin but we have a title, use title as the content
        if len(content) < 50 and title:
            content = title

        context_line = " | ".join(filter(None, [profile.field, profile.affiliation]))
        prompt = (
            f"Person: {profile.name}"
            + (f" ({context_line})" if context_line else "") + "\n"
            f"Source URL: {source.url}\n"
            f"Publisher: {source.publisher}\n"
            f"Content: {content[:600]}"
        )
        if title and title not in content:
            prompt += f"\nTitle: {title}"

        try:
            raw = llm.complete(SYSTEM, prompt)
            data = json.loads(raw)
            for c in data.get("claims", []):
                all_claims.append(Claim(
                    text=c["text"],
                    field=c["field"],
                    source_url=source.url,
                    verification=VerificationState.unverified,
                    date_context=c.get("date_context") or None,
                ))
        except Exception:
            continue

    return _deduplicate(all_claims)


def _deduplicate(claims: list[Claim]) -> list[Claim]:
    seen: set[tuple[str, str]] = set()
    result = []
    for c in claims:
        key = (c.field, c.text[:60])
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result
