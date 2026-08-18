"""Draft QA linter — structured checks mirroring AfC review criteria.

Pure functions over the stored wikitext and session sources; no network I/O
(liveness lives in check_draft_links). Each rule returns zero or more findings
of severity error / warning / info. A draft passes when it has no errors.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import BaseModel

from engine.models import PersonProfile, SourceReliability

Severity = str  # "error" | "warning" | "info"


class Finding(BaseModel):
    id: str
    severity: Severity
    message: str


@dataclass
class QaReport:
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    @property
    def counts(self) -> dict[str, int]:
        return {s: sum(1 for f in self.findings if f.severity == s) for s in ("error", "warning", "info")}


_WEAK_RELIABILITIES = {SourceReliability.self_published, SourceReliability.unreliable}
_LEAD_END = re.compile(r"^==[^=]", re.M)
_ATTRIBUTION = re.compile(
    r"\b(?:reported|recorded|stated|wrote|said|told|quoted)\s+that\b|"
    r"\baccording to\b", re.I)
_REF_SNIPPET = re.compile(r"<ref[^>]*>(.*?)</ref>", re.S)
_CITE_URL = re.compile(r"url\s*=\s*([^|}\s]+)")
_CITE_TITLE = re.compile(r"title\s*=\s*([^}\n]+)")
_CITE_DATE = re.compile(r"date\s*=\s*([^|}\s]+)")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _lead(wikitext: str) -> str:
    m = _LEAD_END.search(wikitext)
    return wikitext[: m.start()] if m else wikitext


def qa_draft(profile: PersonProfile) -> QaReport:
    report = QaReport()
    wikitext = profile.wikitext_en
    if not wikitext:
        report.findings.append(Finding(id="no_draft", severity="error", message="No draft generated yet — generate the draft first."))
        return report

    _check_structure(wikitext, report)
    _check_citations(wikitext, report)
    _check_sources(wikitext, profile, report)
    _check_duplicate_claims(profile, report)
    _check_institutional_achievements(profile, report)
    return report


def _check_duplicate_claims(profile: PersonProfile, report: QaReport) -> None:
    approved = [c for c in profile.claims if c.draft_approved]
    seen_texts: dict[str, str] = {}
    for c in approved:
        text = (c.draft_text or c.text).strip().lower()
        if len(text) < 20:
            continue
        # Compare simplified token set
        tokens = " ".join(re.findall(r"\b\w{4,}\b", text))
        if tokens in seen_texts:
            report.findings.append(Finding(
                id="duplicate_approved_claim",
                severity="warning",
                message=f"Duplicate approved claim detected: '{text[:70]}...' — consolidate into a single statement."
            ))
        else:
            seen_texts[tokens] = text


def _check_institutional_achievements(profile: PersonProfile, report: QaReport) -> None:
    source_map = {s.url: s for s in profile.sources if s.url}
    for c in profile.claims:
        if c.draft_approved and c.field in ("award", "achievement") and c.source_url:
            src = source_map.get(c.source_url)
            if src and (not src.is_independent or src.provenance_category == "institutional_bio"):
                report.findings.append(Finding(
                    id="institutional_achievement_source",
                    severity="warning",
                    message=f"Award/achievement claim '{c.text[:60]}...' cites institutional source ({src.publisher}) — prefer independent secondary coverage."
                ))


def _check_structure(wikitext: str, report: QaReport) -> None:
    if "{{Short description" not in wikitext:
        report.findings.append(Finding(id="short_description", severity="error", message="Missing {{Short description}} at the top of the draft."))
    if "{{Infobox" not in wikitext:
        report.findings.append(Finding(id="infobox", severity="error", message="Missing {{Infobox}} — AfC reviews expect one for biographies."))
    if "{{reflist}}" not in wikitext:
        report.findings.append(Finding(id="reflist", severity="error", message="Missing {{reflist}} — references will not render."))

    lead = _lead(wikitext)
    sentences = len([s for s in re.split(r"(?<=[.!?])\s+", lead.strip()) if s.strip()])
    if sentences < 3:
        report.findings.append(Finding(
            id="thin_lead", severity="warning",
            message=f"Lead is {sentences} sentence{'s' if sentences != 1 else ''} — expand to 3+ sentences with the most notable facts."))

    refs = wikitext.count("<ref")
    if refs < 10:
        report.findings.append(Finding(id="few_refs", severity="error", message=f"Only {refs} references — AfC drafts need substantially more coverage."))

    attribution = [s.strip()[:90] for s in re.split(r"(?<=[.!?])\s+", wikitext) if _ATTRIBUTION.search(s)]
    if attribution:
        report.findings.append(Finding(
            id="attribution_chain", severity="warning",
            message="Prose leans on attribution chains ('X reported that...') — restate facts neutrally. e.g. "
                    + "; ".join(attribution[:3])))

    if "{{Authority control}}" not in wikitext:
        report.findings.append(Finding(id="authority_control", severity="warning", message="Add {{Authority control}} at the bottom."))
    if "{{DEFAULTSORT:" not in wikitext:
        report.findings.append(Finding(id="defaultsort", severity="warning", message="Add {{DEFAULTSORT:Last, First}}."))
    if "[[Category:" not in wikitext:
        report.findings.append(Finding(id="categories", severity="warning", message="Add at least one [[Category:]] — typically [[Category:YYYY births]] and a career category."))
    elif "[[Category:Living people]]" not in wikitext and "[[Category:YYYY births]]" not in wikitext:
        report.findings.append(Finding(id="living_people", severity="info", message="[[Category:Living people]] is missing for a living subject."))
    if "{{Infobox scientist" in wikitext and "| image" not in wikitext:
        report.findings.append(Finding(id="no_image", severity="info", message="No image in the infobox — upload a free-licensed photo if one exists."))


def _check_citations(wikitext: str, report: QaReport) -> None:
    for m in _REF_SNIPPET.finditer(wikitext):
        snippet = m.group(1)
        if "cite " not in snippet and "cite web" not in snippet:
            continue
        for t in _CITE_TITLE.finditer(snippet):
            title = t.group(1).strip()
            if "{{!" in title or " | " in title or "..." in title or "…" in title or title.endswith(("|", ".")):
                report.findings.append(Finding(
                    id="dirty_title", severity="error",
                    message=f"Sloppy citation title: '{title[:70]}' — remove truncation/publisher suffix."))
        for d in _CITE_DATE.finditer(snippet):
            if _ISO_DATE.search(d.group(1)):
                report.findings.append(Finding(
                    id="iso_date", severity="error",
                    message=f"Use dmy dates in citations, not ISO ({d.group(1)[:30]})."))
        if re.search(r"date\s*=\s*", snippet) is None:
            report.findings.append(Finding(id="missing_date", severity="warning", message="A citation has no |date= — add the publication date."))

    for m in re.finditer(r"\[[^]]+\]\(https?://[^)\s]+\)", wikitext):
        report.findings.append(Finding(id="bare_url", severity="error", message=f"Bare external link in prose: '{m.group(0)[:60]}' — wrap it in a {{cite web}}."))


def _check_sources(wikitext: str, profile: PersonProfile, report: QaReport) -> None:
    reliability_by_url = {s.url: s.reliability for s in profile.sources if s.url}
    cited_urls = {u for m in _REF_SNIPPET.finditer(wikitext) for u in _CITE_URL.findall(m.group(1))}
    for url, reliability in reliability_by_url.items():
        if url in cited_urls and reliability in _WEAK_RELIABILITIES:
            report.findings.append(Finding(
                id="weak_source", severity="warning",
                message=f"Cited source is {reliability.value.replace('_', ' ')}: {url[:70]} — prefer reliable secondary coverage."))
