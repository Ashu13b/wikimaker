"""Deterministic Hindi Wikipedia (hi.wikipedia.org) draft generator.

Generates a source-grounded Hindi draft with Hindi Wikipedia infoboxes,
section titles, and citation structures.
"""
from __future__ import annotations

from collections import defaultdict

from engine.models import PersonProfile
from wiki.draft import (
    DraftAudit,
    DraftEvidence,
    audit_profile,
    _display_name,
    _clean,
    _citation,
    _items_for,
    _item_year,
)


def _hindi_infobox(profile: PersonProfile, audit: DraftAudit) -> str:
    """Build a Hindi Wikipedia scientist infobox."""
    evidenced_fields = {item.claim.field for item in audit.evidence}
    name = _display_name(profile)
    rows = [f"| नाम = {name}"]
    if profile.birth_place and "birth_place" in evidenced_fields:
        rows.append(f"| जन्म_स्थान = {_clean(profile.birth_place)}")
    if profile.nationality and "nationality" in evidenced_fields:
        nat = "भारतीय" if profile.nationality.lower() == "indian" else _clean(profile.nationality)
        rows.append(f"| राष्ट्रीयता = {nat}")
    if profile.field and "field" in evidenced_fields:
        rows.append(f"| कार्यक्षेत्र = {_clean(profile.field)}")
    if profile.affiliation and evidenced_fields.intersection({"affiliation", "position", "career"}):
        rows.append(f"| संस्थान = {_clean(profile.affiliation)}")
    if profile.known_for and "known_for" in evidenced_fields:
        rows.append(f"| प्रसिद्धि = {_clean(profile.known_for)}")
    if len(rows) == 1:
        return ""
    return "{{ज्ञानसन्दूक वैज्ञानिक\n" + "\n".join(rows) + "\n}}"


def _render_hindi_items(items: list[DraftEvidence], used_refs: set[str], limit: int | None = None, bulleted: bool = False) -> list[str]:
    selected = items if limit is None else items[:limit]
    rendered = [f"{_clean(item.claim.draft_text or item.claim.text).rstrip('.')}{_citation(item.source, used_refs)}।" for item in selected]
    if bulleted:
        return [f"* {line}" for line in rendered]
    return [" ".join(rendered)] if rendered else []


def render_hindi_draft(profile: PersonProfile, audit: DraftAudit | None = None) -> str:
    """Render valid reviewable Hindi wikitext using only audited evidence."""
    audit = audit or audit_profile(profile)
    if not audit.ready:
        reasons = "; ".join(issue.message for issue in audit.blockers)
        raise ValueError(f"Draft evidence is not ready: {reasons}")

    by_field: dict[str, list[DraftEvidence]] = defaultdict(list)
    for item in audit.evidence:
        by_field[item.claim.field].append(item)

    used_refs: set[str] = set()
    name = _display_name(profile)
    lead_parts: list[str] = []

    field_item = next(iter(by_field.get("field", [])), None)
    affiliation_item = next(iter(by_field.get("affiliation", [])), None)
    position_item = next(iter(by_field.get("position", [])), None)
    nationality = "भारतीय" if (profile.nationality or "").lower() == "indian" else (profile.nationality or "")

    if field_item:
        prefix = f"{nationality} " if nationality else ""
        lead_parts.append(
            f"'''{name}''' एक {prefix}वैज्ञानिक हैं, जिनका मुख्य अनुसंधान कार्य {_clean(field_item.claim.draft_text or field_item.claim.text).rstrip('.')}"
            f"{_citation(field_item.source, used_refs)} पर केंद्रित है।"
        )
    else:
        lead_item = affiliation_item or position_item
        assert lead_item is not None
        lead_parts.append(f"'''{name}''' एक {nationality} वैज्ञानिक हैं{_citation(lead_item.source, used_refs)}।")

    if position_item:
        lead_parts.append(f"{_clean(position_item.claim.draft_text or position_item.claim.text).rstrip('.')}{_citation(position_item.source, used_refs)}।")
    elif affiliation_item:
        lead_parts.append(f"{_clean(affiliation_item.claim.draft_text or affiliation_item.claim.text).rstrip('.')}{_citation(affiliation_item.source, used_refs)}।")

    known_item = next(iter(by_field.get("known_for", [])), None)
    if known_item:
        lead_parts.append(f"{_clean(known_item.claim.draft_text or known_item.claim.text).rstrip('.')}{_citation(known_item.source, used_refs)}।")

    award_item = next(iter(by_field.get("award", [])), None)
    if award_item:
        lead_parts.append(f"{_clean(award_item.claim.draft_text or award_item.claim.text).rstrip('.')}{_citation(award_item.source, used_refs)}।")

    lines = [
        "{{प्रारूप लेख}}",
        "",
    ]
    infobox = _hindi_infobox(profile, audit)
    if infobox:
        lines.extend([infobox, ""])
    lines.extend(lead_parts)

    sections = (
        ("प्रारंभिक जीवन एवं शिक्षा", ("birth_date", "birth_place", "education"), None, False),
        ("करियर", ("career", "affiliation", "position"), None, False),
        ("प्रमुख शोध एवं योगदान", ("known_for", "achievement"), 20, False),
        ("चयनित शोध पत्र", ("publication",), 10, True),
        ("पुरस्कार एवं सम्मान", ("award",), None, False),
    )
    for title, fields, limit, bulleted in sections:
        items = _items_for(audit, fields)
        if title == "करियर" and position_item is not None:
            items = [item for item in items if item is not position_item]
        if title == "प्रमुख शोध एवं योगदान" and known_item is not None:
            items = [item for item in items if item is not known_item]
        if title == "पुरस्कार एवं सम्मान" and award_item is not None:
            items = [item for item in items if item is not award_item]
        if not items:
            continue
        if title == "चयनित शोध पत्र":
            items.sort(key=lambda item: _item_year(item) or 0, reverse=True)
        else:
            items.sort(key=lambda item: _item_year(item) or 9999)
        lines.extend(["", f"== {title} ==", *_render_hindi_items(items, used_refs, limit, bulleted)])

    lines.extend(["", "== सन्दर्भ ==", "{{reflist}}", "", "[[श्रेणी:जीवित लोग]]", "[[श्रेणी:भारतीय वैज्ञानिक]]"])
    return "\n".join(lines).strip() + "\n"
