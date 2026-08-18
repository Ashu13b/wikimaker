from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class SourceReliability(str, Enum):
    reliable_secondary = "reliable_secondary"
    primary = "primary"
    self_published = "self_published"
    unreliable = "unreliable"


class VerificationState(str, Enum):
    unverified = "unverified"    # auto-extracted, not checked by user
    confirmed = "confirmed"      # user opened source and confirmed
    edited = "edited"            # user corrected the extracted text
    skipped = "skipped"          # user chose not to verify


class Source(BaseModel):
    url: str
    title: str
    publisher: str
    reliability: SourceReliability = SourceReliability.primary
    snippet: str = ""
    date: Optional[str] = None
    user_provided: bool = False   # True = user pasted this URL manually
    human_verified: bool = False  # True = user explicitly checked this source

    # Human editorial assessment. A reliable independent source may still be
    # only a passing mention, so it must not automatically become notability
    # evidence. Notes and origin grouping remain in the durable research record
    # even when no claim from the source is selected for a draft.
    coverage_depth: Literal["unassessed", "passing_mention", "significant"] = "unassessed"
    editorial_origin: Optional[str] = None
    research_notes: str = ""

    # Provenance and Trust scoring
    is_independent: bool = True
    domain_trust: str = "medium"             # high|medium|low|untrusted
    provenance_category: str = "general_web" # independent_secondary|authored_publication|institutional_bio|self_published|general_web

    # Where this source came from
    fetched_by: Optional[str] = None  # semantic_scholar|google_search|duckduckgo|crawl|user

    # Liveness & archiving (populated by check_liveness at add/verify time)
    liveness: str = "unknown"  # alive | blocked | dead | unknown
    archive_url: Optional[str] = None  # Wayback URL used as the citation when the source is dead

    # Author match result (populated for DOI/academic sources)
    author_match_status: Optional[str] = None   # confirmed|possible|wrong_person|not_found|no_data
    author_match_name: Optional[str] = None      # matched author as it appears in paper
    author_match_affiliation: Optional[str] = None
    all_paper_authors: list[str] = Field(default_factory=list)

    # Relevance flag (populated for web/news sources)
    relevance_flag: str = "unscored"

    # Where the page actually loaded after redirects ("" = not captured). A
    # meaningful redirect to a different article is surfaced here so the flag
    # and the human reviewer can see the silent trap instead of trusting the URL.
    redirected_to: Optional[str] = None

    # Profile-shaped outbound links found on this page — feed into suggestion queue
    profile_links: list[str] = Field(default_factory=list)

    # Extraction diagnostics (explains why 0 claims were extracted or status of fact parsing)
    extraction_status: Optional[str] = None  # extracted | redundant | thin_content | passing_mention | stub_mode | likely_wrong
    extraction_note: Optional[str] = None


class Claim(BaseModel):
    text: str
    field: str  # birth_date, affiliation, award, publication, education, position, etc.
    source_url: Optional[str] = None   # None = unsourced
    verification: VerificationState = VerificationState.unverified
    user_provided: bool = False        # True = user typed this fact directly
    auto_source_attempted: bool = False  # True = we tried to find a source, failed
    date_context: Optional[str] = None  # e.g. "2005", "2005–2015", "since 2020" — only if verbatim in source
    draft_approved: bool = False  # Explicit editorial decision; verification alone is insufficient
    draft_text: Optional[str] = None  # Neutral paraphrase used by the deterministic renderer

    # Strict Provenance & Trust Scoring
    trust_score: float = 0.5            # 0.0–1.0 trust score
    provenance_status: str = "unverified" # verified_independent|primary_sourced|unverified
    is_independent: bool = False


class NotabilityResult(BaseModel):
    score: float          # 0.0–1.0
    label: str            # "Strong coverage" / "Moderate coverage" / etc.
    rs_count: int         # human-assessed significant independent origins
    reason: str
    candidate_count: int = 0  # independent outlets awaiting/including assessment
    wp_prof_signals: list[str] = Field(default_factory=list)  # academic-specific signals


class PersonCandidate(BaseModel):
    name: str
    photo_url: Optional[str] = None
    bio_snippet: str = ""
    birth_year: Optional[str] = None
    nationality: Optional[str] = None
    field: Optional[str] = None
    affiliation: Optional[str] = None
    wikipedia_url: Optional[str] = None
    wikidata_id: Optional[str] = None


class UrlSuggestion(BaseModel):
    """A ranked candidate URL from the suggestion queue (suggester → frontend).

    Contract for `suggest_next_urls` output; validating at the API boundary means
    a renamed/removed key fails loudly instead of rendering as undefined in the UI.
    """
    url: str
    title: str = ""
    snippet: str = ""
    reason: str = ""
    query: Optional[str] = None
    expected_slots: list[str] = Field(default_factory=list)
    priority: int = 0
    source_type: Optional[Literal["profile", "publication", "news"]] = None
    fetchable: Literal["open", "needs_browser", "paywalled"] = "open"
    relevance: Literal["high", "medium", "low"] = "medium"
    completion_value: int = 0


class ClaimCluster(BaseModel):
    canonical_text: str
    field: str
    corroborating_sources: list[str] = Field(default_factory=list)
    claim_indices: list[int] = Field(default_factory=list)
    repetition_count: int = 1


class ResearchSaturation(BaseModel):
    score: float          # 0.0–1.0 saturation score
    level: str            # "saturated" | "mature" | "exploring"
    repetition_rate: float # 0.0–1.0 percentage of claims that repeat existing facts
    syndication_rate: float # 0.0–1.0 percentage of sources sharing editorial origins/wires
    unique_fact_count: int
    total_claims_analyzed: int
    summary: str
    corroborated_clusters: list[ClaimCluster] = Field(default_factory=list)


class PersonProfile(BaseModel):
    """Central data model. wikimaker fills this; future research hub extends it."""
    name: str
    session_id: Optional[str] = None  # stable identity; name is just a mutable label
    wikidata_id: Optional[str] = None
    wikipedia_url: Optional[str] = None
    photo_url: Optional[str] = None

    # Core facts
    full_name: Optional[str] = None
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    nationality: Optional[str] = None
    field: Optional[str] = None
    affiliation: Optional[str] = None
    known_for: Optional[str] = None
    awards: list[str] = Field(default_factory=list)

    # Research outputs
    sources: list[Source] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    skipped_sources: list[str] = Field(default_factory=list)
    rejected_sources: list[str] = Field(default_factory=list)

    # Notability (informational — never a hard gate)
    notability: Optional[NotabilityResult] = None

    # Research Saturation & Diminishing Returns Analytics
    saturation: Optional[ResearchSaturation] = None

    # Slot analysis — which Wikipedia fields are still missing sources
    missing_slots: list[str] = Field(default_factory=list)

    # Researcher profile IDs (orcid, google_scholar, semantic_scholar, scopus, researchgate)
    researcher_ids: dict[str, str] = Field(default_factory=dict)
    # Which IDs have been validated against affiliation / ORCID API
    confirmed_ids: dict[str, bool] = Field(default_factory=dict)

    # Draft outputs
    wikitext_en: Optional[str] = None
    wikitext_hi: Optional[str] = None
