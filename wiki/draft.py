"""Audit research evidence and render a source-grounded Wikipedia draft.

Drafting is deliberately deterministic.  The renderer only receives claims that
the audit linked to a human-verified source; it never fills gaps with model
knowledge or hard-coded biography text.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from typing import Iterable

from pydantic import BaseModel, Field

from engine.models import Claim, PersonProfile, Source, SourceReliability, VerificationState
from engine.provenance import normalize_url
from engine.publishers import (
    is_independent_secondary_news,
    is_primary_or_institutional,
    extract_domain,
)


class DraftIssue(BaseModel):
    code: str
    message: str
    count: int = 1


class DraftEvidence(BaseModel):
    claim: Claim
    source: Source


class DraftAudit(BaseModel):
    ready: bool
    eligible_claim_count: int
    eligible_source_count: int
    independent_source_count: int
    excluded_claim_count: int
    blockers: list[DraftIssue] = Field(default_factory=list)
    warnings: list[DraftIssue] = Field(default_factory=list)
    exclusions: list[DraftIssue] = Field(default_factory=list)
    evidence: list[DraftEvidence] = Field(default_factory=list)


_NOISE_PATTERNS = (
    re.compile(r"^\s*\d+\s*,?\s*\*"),
    re.compile(r"^read articles by\b", re.I),
    re.compile(r"^we extracted\b", re.I),
    re.compile(r"^isbn\s*:", re.I),
    re.compile(r"^list of staff\b", re.I),
    re.compile(r"^contact\b", re.I),
    re.compile(r"^phone\b", re.I),
    re.compile(r"^discover\b", re.I),
    re.compile(r"^\.{1,3}\s*"),
    re.compile(r"\binviting candidates\b", re.I),
    re.compile(r"\bwalk-in interview\b", re.I),
)

_ROLE_WORDS = ("scientist", "director", "head", "professor", "researcher", "fellow", "joined", "promoted", "investigator")
_CAREER_ACTIVITY_WORDS = ("research stay", "research support", "associateship")
_INSTITUTION_WORDS = ("institute", "university", "college", "centre", "center", "division", "department", "icar", "cirb")
_PUBLICATION_WORDS = ("authored", "co-authored", "coauthored", "co-editor", "coeditor", "published", "publication", "first author", "paper", "study")
_BIRTH_SUBJECT_NOISE = ("calf", "buffalo", "bull", "cow", "animal", "clone", "kg", "delivery")

# Action verbs that signal a substantive research/achievement statement rather
# than an extraction fragment. Substring match, so "co-discover" covers both
# "co-discovered" and "co-discoverer".
_RESEARCH_ACTIONS = (
    "led", "pioneered", "developed", "produced", "reported", "recognized",
    "principal investigator", "completed", "featured", "served", "submitted",
    "co-discover", "research", "achievement", "project",
    "found", "described", "demonstrated", "showed", "noted", "studied",
    "assessed", "evaluated", "examined", "weighed", "identified", "compared",
)


def _host(url: str) -> str:
    return extract_domain(url)


def _is_independent_secondary(source: Source) -> bool:
    if is_primary_or_institutional(source.url):
        return False
    if is_independent_secondary_news(source.url):
        return True
    return (
        source.is_independent
        and source.provenance_category == "independent_secondary"
        and source.reliability == SourceReliability.reliable_secondary
    )


def _source_rank(source: Source) -> int:
    if _is_independent_secondary(source):
        return 3
    if source.provenance_category == "institutional_bio" or _host(source.url).endswith(("icar.org.in", "icar.gov.in", "cirb.res.in")):
        return 2
    if source.provenance_category == "authored_publication" or _host(source.url) in {"doi.org", "orcid.org"}:
        return 1
    return 0


def _claim_exclusion(claim: Claim, source: Source | None) -> str | None:
    text = " ".join((claim.draft_text or claim.text).split())
    if not claim.draft_approved:
        return "claim_not_approved_for_draft"
    lower = text.lower()
    if claim.verification not in {VerificationState.confirmed, VerificationState.edited}:
        return "claim_not_confirmed"
    if not claim.source_url:
        return "claim_has_no_source"
    if source is None:
        return "source_missing_from_session"
    if not source.url.lower().startswith(("http://", "https://")):
        return "source_not_publicly_citable"
    if source.liveness == "dead" and not source.archive_url:
        return "source_url_dead"
    if claim.field in {"known_for", "award"} and _host(source.url) == "satishserial.com":
        return "exceptional_claim_uses_commercial_profile"
    if not source.human_verified:
        return "source_not_human_verified"
    if source.reliability.value == "unreliable":
        return "source_marked_unreliable"
    if source.relevance_flag == "likely_wrong":
        return "source_likely_wrong_person"
    if len(text) < 15:
        return "claim_too_short"
    if any(pattern.search(text) for pattern in _NOISE_PATTERNS):
        return "claim_looks_like_extraction_noise"
    if text.endswith(("&", "Dr", "Dr.", "fl")):
        return "claim_looks_truncated"
    if claim.field in {"birth_date", "birth_place"}:
        # The subject is a person, but extraction sometimes tags a cloned-calf
        # "birth" with the person's own birth_date field. Scan the claim text
        # AND the source title so a clean-text claim sourced to a cloned-calf
        # article ("Born on December 11, 2015") is still caught.
        birth_context = lower + " " + ((source.title or "") if source else "").lower()
        if any(word in birth_context for word in _BIRTH_SUBJECT_NOISE):
            return "claim_appears_to_describe_animal"
        if claim.field == "birth_date" and not re.search(r"\b(?:18|19|20)\d{2}\b", text):
            return "birth_claim_has_no_year"
    if claim.field == "affiliation" and (not any(word in lower for word in _INSTITUTION_WORDS) or text[:1].islower()):
        return "affiliation_claim_has_no_institution"
    if claim.field in {"position", "career"} and not any(
        word in lower for word in (*_ROLE_WORDS, *_CAREER_ACTIVITY_WORDS)
    ):
        return "career_claim_has_no_role"
    if claim.field == "publication" and not any(word in lower for word in _PUBLICATION_WORDS):
        return "publication_claim_not_bibliographic"
    if claim.field == "known_for":
        if len(text) < 35:
            return "research_claim_too_short"
        if not any(word in lower for word in _RESEARCH_ACTIONS):
            return "research_claim_has_no_subject_action"
    return None


def audit_profile(profile: PersonProfile) -> DraftAudit:
    """Resolve confirmed claims to usable sources and explain every exclusion."""
    sources_by_url = {normalize_url(source.url): source for source in profile.sources}
    evidence: list[DraftEvidence] = []
    excluded: Counter[str] = Counter()
    seen: set[tuple[str, str, str]] = set()

    for claim in profile.claims:
        source = sources_by_url.get(normalize_url(claim.source_url)) if claim.source_url else None
        reason = _claim_exclusion(claim, source)
        if reason:
            excluded[reason] += 1
            continue
        assert source is not None
        dedupe_key = (claim.field, " ".join((claim.draft_text or claim.text).lower().split()), normalize_url(source.url))
        if dedupe_key in seen:
            excluded["duplicate_claim"] += 1
            continue
        seen.add(dedupe_key)
        evidence.append(DraftEvidence(claim=claim, source=source))

    evidence.sort(key=lambda item: _source_rank(item.source), reverse=True)

    eligible_urls = {normalize_url(item.source.url) for item in evidence}
    independent_hosts = {
        _host(item.source.url)
        for item in evidence
        if _is_independent_secondary(item.source)
    }

    blockers: list[DraftIssue] = []
    warnings: list[DraftIssue] = []
    if not evidence:
        blockers.append(DraftIssue(code="no_eligible_claims", message="No confirmed claim is linked to a human-verified usable source."))
    if not any(item.claim.field in {"full_name", "field", "affiliation", "position", "career"} for item in evidence):
        blockers.append(DraftIssue(code="no_identity_or_career_evidence", message="No usable identity or career claim is available for the lead."))
    if len(independent_hosts) < 2:
        blockers.append(DraftIssue(
            code="insufficient_independent_coverage",
            message="Fewer than two independent secondary sources support included claims; AfC review expects independent coverage. Verify and approve independent news reports before drafting.",
            count=len(independent_hosts),
        ))
    significant_origins = {
        (item.source.editorial_origin or _host(item.source.url)).strip().lower()
        for item in evidence
        if _is_independent_secondary(item.source)
        and item.source.coverage_depth == "significant"
    }
    significant_origins.discard("")
    if len(significant_origins) < 2:
        warnings.append(DraftIssue(
            code="significant_coverage_not_demonstrated",
            message="Fewer than two editorial origins have been human-assessed as significant person-focused coverage; independent event reports may not establish GNG.",
            count=len(significant_origins),
        ))
    warnings.append(DraftIssue(
        code="academic_notability_requires_review",
        message="Independent project coverage does not by itself prove the academic-notability guideline; a human must assess research impact or another criterion.",
    ))
    # Separate authored/primary evidence from independent notability evidence:
    # notability-bearing claims (known_for / award) resting only on
    # non-independent sources are a coverage risk even when notability is shown
    # elsewhere. Warning only — the claim stays in the draft.
    achievement_on_primary = [
        item for item in evidence
        if item.claim.field in {"known_for", "achievement", "award"} and not _is_independent_secondary(item.source)
    ]
    if achievement_on_primary:
        warnings.append(DraftIssue(
            code="achievement_claim_not_independent",
            message="Achievement claims (known_for/award) rest only on non-independent sources; AfC notability expects independent secondary coverage for these.",
            count=len(achievement_on_primary),
        ))
    if excluded:
        warnings.append(DraftIssue(
            code="claims_excluded",
            message="Some collected claims were excluded from drafting because they did not meet evidence rules.",
            count=sum(excluded.values()),
        ))

    exclusions = [
        DraftIssue(code=code, message=code.replace("_", " ").capitalize(), count=count)
        for code, count in sorted(excluded.items())
    ]
    return DraftAudit(
        ready=not blockers,
        eligible_claim_count=len(evidence),
        eligible_source_count=len(eligible_urls),
        independent_source_count=len(independent_hosts),
        excluded_claim_count=sum(excluded.values()),
        blockers=blockers,
        warnings=warnings,
        exclusions=exclusions,
        evidence=evidence,
    )


def _clean(value: str) -> str:
    return " ".join(value.split()).replace("<", "&lt;").replace(">", "&gt;")


def _title_clean(value: str) -> str:
    """Strip fetch-time junk from page titles: '...' truncation and ' | Site' suffixes.

    Page titles captured by fetchers often end with an ellipsis (truncated) or a
    '| publisher' suffix; a reviewer sees those as sloppy citations.
    """
    title = " ".join(value.split())
    # 'Telomerase ... | IntechOpen' → drop the short suffix after ' | '
    if " | " in title:
        head, _, tail = title.rpartition(" | ")
        if len(tail) < 40 and " " not in tail.strip():
            title = head
    had_ellipsis = title.endswith(("...", "…"))
    if had_ellipsis:
        title = title[: -len("...")] if title.endswith("...") else title[:-1]
    if had_ellipsis:
        # Truncation often leaves a dangling preposition: 'Central Institute for ...'
        title = re.sub(r"\s+(?:for|and|of|at|the|in|by|on|with|from|to)\s*$", "", title)
    if title.endswith(".") and not re.search(r"[A-Z]\.$", title):
        title = title[:-1]
    return title.strip().rstrip(",")


_MONTHS = ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]
_MONTH_NUM = {name.lower(): i for i, name in enumerate(_MONTHS) if i}


def _format_date(value: str) -> str:
    """Normalize source dates to the dmy style Wikipedia bios expect."""
    v = value.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        month = int(m.group(2))
        if 1 <= month <= 12:
            return f"{int(m.group(3))} {_MONTHS[month]} {m.group(1)}"
    m = re.fullmatch(r"([A-Za-z]+) (\d{1,2}), (\d{4})", v)
    if m and m.group(1).lower() in _MONTH_NUM:
        return f"{int(m.group(2))} {_MONTH_NUM[m.group(1).lower()]} {m.group(3)}"
    return v


def _format_birth_date(value: str) -> str:
    """Full dates become {{birth date and age}}, partial values pass through."""
    m = re.fullmatch(r"([A-Za-z]+) (\d{1,2}), (\d{4})", value.strip())
    if m and m.group(1).lower() in _MONTH_NUM:
        return f"{{{{birth date and age|{m.group(3)}|{_MONTH_NUM[m.group(1).lower()]}|{int(m.group(2))}}}}}"
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
    if m:
        return f"{{{{birth date and age|{m.group(1)}|{int(m.group(2))}|{int(m.group(3))}}}}}"
    return _format_date(value)


def _display_name(profile: PersonProfile) -> str:
    value = profile.full_name or profile.name
    return _clean(re.sub(r"^(?:Dr\.?|Prof\.?)\s+", "", value, flags=re.I))


def _short_description(profile: PersonProfile) -> str:
    nationality = _clean(profile.nationality or "")
    if profile.field:
        focus = re.split(r"\s*(?:&|\band\b|,)\s*", profile.field, maxsplit=1, flags=re.I)[0]
        value = f"{nationality} {focus.lower()} researcher".strip()
    else:
        value = f"{nationality} scientist".strip()
    return value[:1].upper() + value[1:]


def _cite_value(value: str) -> str:
    cleaned = _clean(value).replace("}}", "&#125;&#125;").replace("{{", "&#123;&#123;")
    return cleaned.replace("|", "{{!}}")


def _ref_name(url: str) -> str:
    return "src-" + hashlib.sha1(normalize_url(url).encode()).hexdigest()[:10]


def _archive_date(archive_url: str) -> str | None:
    """Extract the snapshot date from a Wayback URL: /web/YYYYMMDDHHMMSS/."""
    match = re.search(r"/web/(\d{4})(\d{2})(\d{2})\d{6}/", archive_url)
    if not match:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if not 1 <= month <= 12:
        return None
    return f"{day} {_MONTHS[month]} {year}"


def _citation(source: Source, used: set[str]) -> str:
    name = _ref_name(source.url)
    if name in used:
        return f'<ref name="{name}" />'
    used.add(name)
    fields = [
        "{{cite web",
        f"url={_cite_value(source.url)}",
        f"title={_cite_value(_title_clean(source.title or source.url))}",
    ]
    if source.publisher:
        fields.append(f"website={_cite_value(source.publisher)}")
    if source.date:
        fields.append(f"date={_cite_value(_format_date(source.date))}")
    if source.archive_url:
        fields.append(f"archive-url={_cite_value(source.archive_url)}")
        archive_date = _archive_date(source.archive_url)
        if archive_date:
            fields.append(f"archive-date={_cite_value(archive_date)}")
    return f'<ref name="{name}">' + "|".join(fields) + "}}</ref>"


def _items_for(audit: DraftAudit, fields: Iterable[str]) -> list[DraftEvidence]:
    wanted = set(fields)
    return [item for item in audit.evidence if item.claim.field in wanted]


def _claim_text(item: DraftEvidence) -> str:
    return _clean(item.claim.draft_text or item.claim.text).rstrip(".")


def _item_year(item: DraftEvidence) -> int | None:
    """Return the first explicit year attached to a claim or its source."""
    values = (item.claim.date_context, item.claim.draft_text, item.claim.text, item.source.date)
    for value in values:
        match = re.search(r"\b(?:18|19|20)\d{2}\b", value or "")
        if match:
            return int(match.group())
    return None


def _render_items(items: list[DraftEvidence], used_refs: set[str], limit: int | None = None, bulleted: bool = False) -> list[str]:
    selected = items if limit is None else items[:limit]
    rendered = [f"{_claim_text(item)}{_citation(item.source, used_refs)}." for item in selected]
    if bulleted:
        return [f"* {line}" for line in rendered]
    return [" ".join(rendered)] if rendered else []


def _infobox(profile: PersonProfile, audit: DraftAudit) -> str:
    """Build an infobox only from structured values with approved evidence.

    A structured value is not enough by itself: the corresponding field must
    also have draft-approved evidence. This keeps a removed private or weakly
    sourced fact from leaking back into the AfC through the infobox.
    """
    evidenced_fields = {item.claim.field for item in audit.evidence}
    rows = [f"| name = {_display_name(profile)}"]
    if profile.birth_date and "birth_date" in evidenced_fields:
        rows.append(f"| birth_date = {_format_birth_date(profile.birth_date)}")
    if profile.birth_place and "birth_place" in evidenced_fields:
        rows.append(f"| birth_place = {_clean(profile.birth_place)}")
    if profile.nationality and "nationality" in evidenced_fields:
        rows.append(f"| nationality = {_clean(profile.nationality)}")
    if profile.field and "field" in evidenced_fields:
        rows.append(f"| field = {_clean(profile.field)}")
    if profile.affiliation and evidenced_fields.intersection({"affiliation", "position", "career"}):
        rows.append(f"| workplaces = {_clean(profile.affiliation)}")
    if profile.known_for and "known_for" in evidenced_fields:
        rows.append(f"| known_for = {_clean(profile.known_for)}")
    if len(rows) == 1:
        return ""
    return "{{Infobox scientist\n" + "\n".join(rows) + "\n}}"


def _defaultsort(name: str) -> str:
    parts = [p for p in name.replace("Dr.", "").split() if p]
    if len(parts) < 2:
        return name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def render_draft(profile: PersonProfile, audit: DraftAudit | None = None) -> str:
    """Render valid reviewable wikitext using only audited evidence."""
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
    nationality = _clean(profile.nationality) if profile.nationality else ""

    if field_item:
        article = "an" if nationality[:1].lower() in "aeiou" else "a"
        prefix = f"{nationality} " if nationality else ""
        lead_parts.append(
            f"'''{name}''' is {article} {prefix}scientist whose research focuses on {_claim_text(field_item)}"
            f"{_citation(field_item.source, used_refs)}."
        )
    else:
        lead_item = affiliation_item or position_item
        assert lead_item is not None
        lead_parts.append(f"'''{name}''' is a scientist{_citation(lead_item.source, used_refs)}.")
    if position_item:
        lead_parts.append(f"{_claim_text(position_item)}{_citation(position_item.source, used_refs)}.")
    elif affiliation_item:
        lead_parts.append(f"{_claim_text(affiliation_item)}{_citation(affiliation_item.source, used_refs)}.")
    known_item = next(iter(by_field.get("known_for", [])), None)
    if known_item:
        lead_parts.append(f"{_claim_text(known_item)}{_citation(known_item.source, used_refs)}.")
    award_item = next(iter(by_field.get("award", [])), None)
    if award_item:
        lead_parts.append(f"{_claim_text(award_item)}{_citation(award_item.source, used_refs)}.")

    lines = [
        "{{Draft article}}",
        f"{{{{Short description|{_short_description(profile)}}}}}",
        "",
    ]
    infobox = _infobox(profile, audit)
    if infobox:
        lines.extend([infobox, ""])
    lines.extend(lead_parts)

    sections = (
        ("Education", ("birth_date", "birth_place", "education"), None, False),
        ("Career", ("career", "affiliation", "position"), None, False),
        ("Research", ("known_for", "achievement"), 20, False),
        ("Selected publications", ("publication",), 10, True),
        ("Awards and recognition", ("award",), None, False),
    )
    for title, fields, limit, bulleted in sections:
        items = _items_for(audit, fields)
        if title == "Career" and position_item is not None:
            items = [item for item in items if item is not position_item]
        if title == "Research" and known_item is not None:
            # The lead's known_for sentence must not repeat at the top of Research.
            items = [item for item in items if item is not known_item]
        if title == "Awards and recognition" and award_item is not None:
            items = [item for item in items if item is not award_item]
        if not items:
            continue
        if title == "Selected publications":
            items.sort(key=lambda item: _item_year(item) or 0, reverse=True)
        else:
            items.sort(key=lambda item: _item_year(item) or 9999)
        lines.extend(["", f"=={title}==", *_render_items(items, used_refs, limit, bulleted)])

    lines.extend(["", "==References==", "{{reflist}}", "", "{{Authority control}}",
                  f"{{{{DEFAULTSORT:{_defaultsort(name)}}}}}", "[[Category:Living people]]"])
    return "\n".join(lines).strip() + "\n"
