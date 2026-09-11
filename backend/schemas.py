"""Pydantic request/response models for the wikimaker API."""
from __future__ import annotations

from pydantic import BaseModel
from typing import Literal, Optional


class IdentifyRequest(BaseModel):
    name: str
    field: Optional[str] = None
    affiliation: Optional[str] = None


class ResearchRequest(BaseModel):
    name: str
    wikidata_id: Optional[str] = None
    wikipedia_url: Optional[str] = None
    photo_url: Optional[str] = None
    field: Optional[str] = None
    affiliation: Optional[str] = None
    nationality: Optional[str] = None
    birth_year: Optional[str] = None


class AddSourceRequest(BaseModel):
    profile_name: str
    url: str
    title: Optional[str] = None
    text: Optional[str] = None


class AssessSourceRequest(BaseModel):
    """Human editorial assessment retained with a research source."""
    profile_name: str
    url: str
    coverage_depth: Literal["unassessed", "passing_mention", "significant"]
    editorial_origin: Optional[str] = None
    research_notes: str = ""

class AddDocumentFact(BaseModel):
    """A fact the user typed from a document — has no web source, timeline only."""
    profile_name: str
    field: str
    text: str


class AddSourcedClaimRequest(BaseModel):
    """A fact the user read directly in a source and wants bound to it."""
    profile_name: str
    url: str
    field: str
    text: str
    date_context: Optional[str] = None


class VerifyClaimRequest(BaseModel):
    claim_index: int
    action: str   # confirm | edit | skip | approve_draft | remove_draft
    edited_text: Optional[str] = None  # only for action=edit


class BatchVerifyClaimsRequest(BaseModel):
    action: str  # approve_all_usable | confirm_all | skip_unverified


class AddSourcePaste(BaseModel):
    """User pasted text from a blocked page, screenshot, or PDF."""
    profile_name: str
    url: str           # the real URL (for citation) — even if we couldn't fetch it
    pasted_text: str   # what the user copied from the page


class CrawlRequest(BaseModel):
    profile_name: str
    seed_urls: list[str]
    keywords: list[str] = []
    max_nodes: int = 40
    max_depth: int = 3


class TargetedSearchRequest(BaseModel):
    profile_name: str
    slot: str
    hint: Optional[str] = None


class DraftRequest(BaseModel):
    profile_name: str


class FindIdsRequest(BaseModel):
    profile_name: str


class RefreshPapersRequest(BaseModel):
    profile_name: str
    id_type: str   # orcid | semantic_scholar
    id_value: str
    confirm: bool = False  # if True, mark as confirmed before refreshing
