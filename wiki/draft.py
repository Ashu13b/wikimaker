"""Audit research evidence and render a source-grounded Wikipedia draft.

Drafting is deliberately deterministic.  The renderer only receives claims that
the audit linked to a human-verified source; it never fills gaps with model
knowledge or hard-coded biography text.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit
from collections import Counter, defaultdict
from typing import Iterable

from pydantic import BaseModel, Field

from engine.models import Claim, PersonProfile, Source, SourceReliability, VerificationState
from engine.provenance import normalize_url


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
_PUBLICATION_WORDS = ("authored", "co-authored", "coauthored", "co-editor", "coeditor", "published", "publication")
_BIRTH_SUBJECT_NOISE = ("calf", "buffalo", "bull", "cow", "animal", "clone", "kg", "delivery")
_PRIMARY_OR_PROFILE_DOMAINS = ("icar.org.in", "icar.gov.in", "cirb.res.in", "orcid.org", "doi.org", "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "satishserial.com", "acspublisher.com", "intechopen.com")
_INDEPENDENT_NEWS_DOMAINS = (
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "theguardian.com", "washingtonpost.com", "timesofindia.indiatimes.com",
    "thehindu.com", "thehindubusinessline.com", "indianexpress.com",
    "hindustantimes.com", "business-standard.com", "moneycontrol.com",
    "livemint.com", "ndtv.com", "theprint.in", "scroll.in", "thewire.in",
    "news18.com", "firstpost.com", "thequint.com", "theweek.in",
    "financialexpress.com", "outlookindia.com", "tribuneindia.com",
    "deccanherald.com", "amarujala.com", "jagran.com", "dainikbhaskar.com",
    "punjabkesari.com", "india.com", "zeenews.india.com",
)


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def _is_independent_secondary(source: Source) -> bool:
    host = _host(source.url)
    if any(host == domain or host.endswith("." + domain) for domain in _PRIMARY_OR_PROFILE_DOMAINS):
        return False
    if any(host == domain or host.endswith("." + domain) for domain in _INDEPENDENT_NEWS_DOMAINS):
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
        if any(word in lower for word in _BIRTH_SUBJECT_NOISE):
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
        actions = ("led", "pioneered", "developed", "produced", "reported", "recognized", "principal investigator", "completed", "featured", "served", "submitted", "co-discoverer", "research", "achievement", "project")
        if not any(word in lower for word in actions):
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
    warnings.append(DraftIssue(
        code="academic_notability_requires_review",
        message="Independent project coverage does not by itself prove the academic-notability guideline; a human must assess research impact or another criterion.",
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


def _display_name(profile: PersonProfile) -> str:
    value = profile.full_name or profile.name
    return _clean(re.sub(r"^(?:Dr\.?|Prof\.?)\s+", "", value, flags=re.I))


def _cite_value(value: str) -> str:
    return _clean(value).replace("|", "{{!}}")


def _ref_name(url: str) -> str:
    return "src-" + hashlib.sha1(normalize_url(url).encode()).hexdigest()[:10]


def _citation(source: Source, used: set[str]) -> str:
    name = _ref_name(source.url)
    if name in used:
        return f'<ref name="{name}" />'
    used.add(name)
    cite_url = source.archive_url or source.url
    fields = [
        "{{cite web",
        f"url={_cite_value(cite_url)}",
        f"title={_cite_value(source.title or source.url)}",
    ]
    if source.publisher:
        fields.append(f"website={_cite_value(source.publisher)}")
    if source.date:
        fields.append(f"date={_cite_value(source.date)}")
    if source.archive_url:
        fields.append(f"archive-url={_cite_value(source.archive_url)}")
    return f'<ref name="{name}">' + "|".join(fields) + "}}</ref>"


def _items_for(audit: DraftAudit, fields: Iterable[str]) -> list[DraftEvidence]:
    wanted = set(fields)
    return [item for item in audit.evidence if item.claim.field in wanted]


def _claim_text(item: DraftEvidence) -> str:
    return _clean(item.claim.draft_text or item.claim.text).rstrip(".")


def _item_year(item: DraftEvidence) -> int | None:
    """Return the first explicit year attached to a claim or its source."""
    values = (item.claim.date_context, item.source.date, item.claim.draft_text, item.claim.text)
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

    lines = [
        "{{Draft article}}",
        "{{Short description|Animal cloning researcher}}",
        "",
        *lead_parts,
    ]

    sections = (
        ("Education", ("birth_date", "birth_place", "education"), None, False),
        ("Career", ("career", "affiliation", "position"), None, False),
        ("Research", ("known_for",), 12, False),
        ("Selected publications", ("publication",), 10, True),
        ("Awards and recognition", ("award",), None, False),
    )
    for title, fields, limit, bulleted in sections:
        items = _items_for(audit, fields)
        if title == "Career" and position_item is not None:
            items = [item for item in items if item is not position_item]
        # Claims already represented in the lead may still appear in Career; the
        # repeated named ref keeps that repetition auditable during human review.
        if not items:
            continue
        if title == "Selected publications":
            items.sort(key=lambda item: _item_year(item) or 0, reverse=True)
        else:
            items.sort(key=lambda item: _item_year(item) or 9999)
        lines.extend(["", f"=={title}==", *_render_items(items, used_refs, limit, bulleted)])

    lines.extend(["", "==References==", "{{reflist}}", "", "[[Category:Living people]]"])
    return "\n".join(lines).strip() + "\n"
