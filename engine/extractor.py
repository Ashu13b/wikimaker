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
- birth_date: the PERSON's own date or year of birth — NOT birth of an animal, technology, institution, or idea mentioned in the source. Crucially, DO NOT extract the birth date/year of a cloned animal, offspring, calf, or breed (e.g. Garima, Samrupa, Dolly) as the person's birth date, even if the person participated in or led the cloning project.
- birth_place: the PERSON's own birthplace — not a location in a paper title or abstract
- publication: a paper or book authored BY this person — not a citation or reference to others' work
- award: an honour received BY this person — not an award mentioned in passing
Only extract a field if the source clearly states it about this specific person.

date_context rules (critical):
- Only set date_context if a year or date range appears VERBATIM in the source text for that claim.
- Valid examples: "2005", "2005–2015", "since 2020", "1990s", "July 2008"
- If no year is explicitly stated for this fact in the source, omit date_context entirely.
- NEVER infer or guess a date from context. "received the award" → no date_context."""


def _validate_and_filter_claims(claims: list[Claim], profile: PersonProfile) -> list[Claim]:
    import re
    
    def get_year(text: str | None) -> int | None:
        if not text:
            return None
        m = re.search(r'\b(1[89]\d\d|20\d\d)\b', text)
        return int(m.group(1)) if m else None

    # Find the earliest year from non-birth claims in the profile or in the new claims
    all_other_years = []
    for c in profile.claims:
        if c.field != "birth_date":
            y = get_year(c.date_context) or get_year(c.text)
            if y:
                all_other_years.append(y)
    for c in claims:
        if c.field != "birth_date":
            y = get_year(c.date_context) or get_year(c.text)
            if y:
                all_other_years.append(y)

    earliest_other_year = min(all_other_years) if all_other_years else None

    animal_kws = {
        "cloned", "cloning", "animal", "buffalo", "calf", "cow", "bull", "sheep", "goat",
        "offspring", "garima", "samrupa", "ganga", "dolly", "litter", "breed", "species", "surrogate"
    }

    result = []
    for c in claims:
        if c.field == "birth_date":
            text_lower = c.text.lower()
            # Check for animal cloning keywords
            has_animal_kw = any(kw in text_lower for kw in animal_kws)
            
            # Check for logical date inconsistency
            birth_year = get_year(c.date_context) or get_year(c.text)
            is_inconsistent = False
            if birth_year:
                if earliest_other_year and birth_year >= earliest_other_year - 15:
                    is_inconsistent = True
                elif birth_year >= 2000:
                    # Unreasonably recent for a senior/practicing scientist
                    is_inconsistent = True

            if has_animal_kw:
                # Re-classify as known_for since animal cloning birth is a key scientific achievement
                if len(c.text) > 30:
                    c.field = "known_for"
                    result.append(c)
                continue
            elif is_inconsistent:
                # If logically inconsistent and no animal keywords, discard it as a faulty birth date
                continue
                
        result.append(c)
    return result


def filter_person_snippets(text: str, person_name: str, window: int = 3) -> str:
    """Extract only lines matching person's name tokens + window lines before/after for token-efficient PDF processing."""
    if not text:
        return ""
    lines = text.split("\n")
    tokens = [t.lower() for t in person_name.split() if len(t) > 2]
    matched_indices = set()
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(t in line_lower for t in tokens):
            for idx in range(max(0, i - window), min(len(lines), i + window + 1)):
                matched_indices.add(idx)
    if not matched_indices:
        return text[:800]
    sorted_indices = sorted(matched_indices)
    extracted_blocks = []
    current_block = []
    prev_idx = -10
    for idx in sorted_indices:
        if idx > prev_idx + 1 and current_block:
            extracted_blocks.append("\n".join(current_block))
            current_block = []
        current_block.append(lines[idx])
        prev_idx = idx
    if current_block:
        extracted_blocks.append("\n".join(current_block))
    return "\n---\n".join(extracted_blocks)[:1200]


def extract_claims(profile: PersonProfile, sources: list[Source], llm: LLMProvider) -> list[Claim]:
    from .provenance import classify_source_provenance, evaluate_claim_trust

    all_claims: list[Claim] = []
    source_map = {s.url: classify_source_provenance(s, profile.name) for s in sources}

    # prioritise RS sources, then process all with a source
    ordered = sorted(sources, key=lambda s: s.reliability != SourceReliability.reliable_secondary)

    for source in ordered[:8]:  # cap to avoid token overrun
        # Skip sources flagged as the wrong person
        if source.relevance_flag == "likely_wrong":
            continue

        classified_source = source_map.get(source.url, source)

        # Build content block: prefer snippet; fall back to title as surrogate
        content = source.snippet or ""
        if len(content) > 1000 or ".pdf" in source.url.lower():
            content = filter_person_snippets(content, profile.name)
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
            f"Content: {content[:1200]}"
        )
        if title and title not in content:
            prompt += f"\nTitle: {title}"

        try:
            raw = llm.complete(SYSTEM, prompt)
            clean_raw = raw.strip()
            if clean_raw.startswith("```"):
                parts = clean_raw.split("```")
                if len(parts) >= 2:
                    clean_raw = parts[1]
                    if clean_raw.startswith("json"):
                        clean_raw = clean_raw[4:].strip()
            data = json.loads(clean_raw)
            for c in data.get("claims", []):
                claim_obj = Claim(
                    text=c["text"],
                    field=c["field"],
                    source_url=source.url,
                    verification=VerificationState.unverified,
                    date_context=c.get("date_context") or None,
                )
                evaluated = evaluate_claim_trust(claim_obj, classified_source, profile)
                all_claims.append(evaluated)
        except Exception:
            continue

    validated = _validate_and_filter_claims(all_claims, profile)
    return _deduplicate(validated)


def _deduplicate(claims: list[Claim]) -> list[Claim]:
    seen: set[tuple[str, str]] = set()
    result = []
    for c in claims:
        key = (c.field, c.text[:60])
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result
