"""Notability scoring — informational only, never blocks draft generation."""
from __future__ import annotations
import requests
from .models import Source, SourceReliability, NotabilityResult

S2_API = "https://api.semanticscholar.org/graph/v1"


def score_notability(name: str, sources: list[Source]) -> NotabilityResult:
    rs = [s for s in sources if s.reliability == SourceReliability.reliable_secondary]
    rs_count = len(rs)

    wp_prof_signals: list[str] = []
    s2 = _semantic_scholar_signals(name)
    if s2.get("citation_count", 0) >= 50:
        wp_prof_signals.append(f"{s2['citation_count']} citations (Semantic Scholar)")
    if s2.get("paper_count", 0) >= 10:
        wp_prof_signals.append(f"{s2['paper_count']} publications")
    if s2.get("h_index", 0) >= 5:
        wp_prof_signals.append(f"h-index {s2['h_index']}")

    # Score: RS sources are primary signal; WP:PROF signals add weight
    base = min(rs_count / 3, 1.0)
    boost = min(len(wp_prof_signals) * 0.1, 0.3)
    score = round(min(base + boost, 1.0), 2)

    if score >= 0.8:
        label = "Strong"
        reason = f"{rs_count} reliable secondary sources. Likely to pass AfC."
    elif score >= 0.5:
        label = "Moderate"
        reason = f"{rs_count} reliable secondary sources. Borderline — AfC reviewers may request more coverage."
    elif score >= 0.2:
        label = "Weak"
        reason = f"Only {rs_count} reliable secondary source(s). Add more independent news or academic coverage."
    else:
        label = "Insufficient"
        reason = "No reliable secondary sources found yet. AfC will decline without independent coverage."

    return NotabilityResult(
        score=score,
        label=label,
        rs_count=rs_count,
        reason=reason,
        wp_prof_signals=wp_prof_signals,
    )


def _semantic_scholar_signals(name: str) -> dict:
    try:
        resp = requests.get(f"{S2_API}/author/search",
            params={"query": name, "fields": "citationCount,paperCount,hIndex", "limit": 1},
            timeout=8)
        resp.raise_for_status()
        authors = resp.json().get("data", [])
        if not authors:
            return {}
        a = authors[0]
        return {
            "citation_count": a.get("citationCount", 0),
            "paper_count": a.get("paperCount", 0),
            "h_index": a.get("hIndex", 0),
        }
    except Exception:
        return {}
