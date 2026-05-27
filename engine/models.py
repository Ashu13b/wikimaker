from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
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

    # Where this source came from
    fetched_by: Optional[str] = None  # semantic_scholar|google_search|duckduckgo|crawl|user

    # Author match result (populated for DOI/academic sources)
    author_match_status: Optional[str] = None   # confirmed|possible|wrong_person|not_found|no_data
    author_match_name: Optional[str] = None      # matched author as it appears in paper
    author_match_affiliation: Optional[str] = None
    all_paper_authors: list[str] = Field(default_factory=list)

    # Relevance flag (populated for web/news sources)
    relevance_flag: str = "unscored"

    # Profile-shaped outbound links found on this page — feed into suggestion queue
    profile_links: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    text: str
    field: str  # birth_date, affiliation, award, publication, education, position, etc.
    source_url: Optional[str] = None   # None = unsourced
    verification: VerificationState = VerificationState.unverified
    user_provided: bool = False        # True = user typed this fact directly
    auto_source_attempted: bool = False  # True = we tried to find a source, failed
    date_context: Optional[str] = None  # e.g. "2005", "2005–2015", "since 2020" — only if verbatim in source


class NotabilityResult(BaseModel):
    score: float          # 0.0–1.0
    label: str            # "Strong" / "Moderate" / "Weak" / "Insufficient"
    rs_count: int         # reliable secondary source count
    reason: str
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


class PersonProfile(BaseModel):
    """Central data model. wikimaker fills this; future research hub extends it."""
    name: str
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

    # Notability (informational — never a hard gate)
    notability: Optional[NotabilityResult] = None

    # Slot analysis — which Wikipedia fields are still missing sources
    missing_slots: list[str] = Field(default_factory=list)

    # Researcher profile IDs (orcid, google_scholar, semantic_scholar, scopus, researchgate)
    researcher_ids: dict[str, str] = Field(default_factory=dict)
    # Which IDs have been validated against affiliation / ORCID API
    confirmed_ids: dict[str, bool] = Field(default_factory=dict)

    # Draft outputs
    wikitext_en: Optional[str] = None
    wikitext_hi: Optional[str] = None
