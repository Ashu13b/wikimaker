<!-- context-kit CODE_MAP · v0.1.0 · generated 2026-07-28 18:59 UTC · sha ed1e512 · host vnic-trading -->

# CODE_MAP

Symbol index (skim-grade). Consult before Grep/Read.

## Composition
- Python — 26 files · 269 symbols
- TypeScript — 16 files · 130 symbols
- CSS — 1 file (unindexed)
- HTML — 1 file (unindexed)
- Shell Script — 1 file (unindexed)
_Total: 45 files · 399 symbols across 5 languages._


## Compartments
- `auto` — dynamic (git files in play + 2-hop import neighborhood)

Run `ck compartment <name>` to load a compartment's warm symbol index.

### ./
- `browser_server.py` — PROFILE_DIR, XVFB_DISPLAY, PORT, class _Cmd, _q, _headed, _running, _xvfb, def _dispatch, def _try_start_xvfb, def _browser_thread, def lifespan, app, def screenshot, class NavReq, def navigate, def info, class ViewportReq, def set_viewport, class ClickReq, def click, class TypeReq, def type_text, class KeyReq, def press_key, class ScrollReq, def scroll, def go_back, def go_forward, def reload, def get_content, def status, def index, BROWSER_HTML, def start_browser, def stop_browser
- `generate_draft.py` — session_file, hindi, data, profile, llm, wikitext, out_en
### backend/
- `backend/main.py` — SESSIONS_DIR, app, _llm, def llm, class IdentifyRequest, class ResearchRequest, class AddSourceRequest, class AddDocumentFact, class VerifyClaimRequest, class AddSourcePaste, class CrawlRequest, class TargetedSearchRequest, class DraftRequest, _sessions, _wiki_statuses, def _session_path, def _apply_provenance, def _save_session, def _load_session_file, BROWSER_SERVER, def _push_to_browser, def _get_profile, def _check_doi_sources, def identify, def research_start, def add_source, def _add_sd_article, def _add_sd_author_profile, def add_document_fact, def verify_claim, def add_source_paste, def deep_crawl, def targeted_search_endpoint, def generate_draft, def get_session, def verify_source, def reject_source, def list_sessions, def delete_session, class FindIdsRequest, class RefreshPapersRequest, def find_researcher_ids_endpoint, def refresh_papers_endpoint, def resume_session, def fetch_from_browser, def suggest_urls, def lifespan, api_app, unified_app, FRONTEND_DIST, app
### engine/
- `engine/author_check.py` — CROSSREF_API, TIMEOUT, def name_variants, def _normalise, def _author_matches_variants, def _affiliation_matches, def check_doi_authors, def extract_doi
- `engine/classifier.py` — _RS_DOMAINS, _PRIMARY_DOMAINS, _SELF_DOMAINS, _UNRELIABLE_DOMAINS, def _domain_classify, SYSTEM, def classify_sources
- `engine/crawler.py` — TIMEOUT, S2_API, class SourceNode, class SourceGraph(to_sources), def crawl, def _extract_meta, def _extract_links, def _extract_dois, def _extract_entities, def _count_mentions, def _is_relevant_link, def _entity_worth_searching, def _search_entity, def _temporal_variants, def _expand_doi
- `engine/extractor.py` — WIKI_SLOTS, SLOT_SOURCE_HINTS, def find_missing_slots, SYSTEM, def _validate_and_filter_claims, def extract_claims, def _deduplicate
- `engine/fetcher.py` — HEADERS, BOT_HEADERS, TIMEOUT, class FetchResult(__init__), BROWSER_SERVER, def _try_browser_server, def fetch_url, def fetch_orcid_by_name, def fetch_text_paste, def _direct_fetch, def _pdf_extract, def _wayback_fetch, def _orcid_fetch, def _fetch_orcid_id, def _orcid_to_text, def _extract_text
- `engine/fetcher_browser.py` — _SESSION_DIR, _BLOCKED_SIGNALS, _LAUNCH_ARGS, _STEALTH_JS, _UA, def fetch_with_browser
- `engine/identifier.py` — HEADERS, WIKI_API, WIKIDATA_API, def fetch_wikidata_photo, def fetch_wikidata_photo_by_id, def find_candidates, _HONORIFICS, def _significant_tokens, def _name_matches, def _search_wikipedia, def _search_wikidata, def _wikipedia_detail, def _wikidata_detail, def _wikidata_image, def _looks_like_person, def _strip_html
- `engine/link_extractor.py` — _PROFILE_DOMAINS, _PROFILE_PATH_FRAGMENTS, def extract_profile_links
- `engine/llm.py` — class LLMProvider(complete), class ClaudeProvider(__init__, complete), class GeminiProvider(__init__, complete), class LocalProvider(complete), class NullProvider(complete), class StubProvider(complete, _classify, _extract, _draft), def get_provider
- `engine/models.py` — class SourceReliability, class VerificationState, class Source, class Claim, class NotabilityResult, class PersonCandidate, class PersonProfile
- `engine/notability.py` — S2_API, def score_notability, def _semantic_scholar_signals
- `engine/provenance.py` — HIGH_TRUST_DOMAINS, MEDIUM_TRUST_DOMAINS, UNTRUSTED_DOMAINS, def get_domain_trust, def classify_source_provenance, def evaluate_claim_trust
- `engine/relevance.py` — _WRONG_PERSON_SIGNALS, _ACADEMIC_FETCHED_BY, _DOI_PATTERNS, def _significant_name_tokens, def flag_source, def flag_sources
- `engine/researcher.py` — HEADERS, S2_API, GOOGLE_CSE_URL, def fetch_auto_sources, def fetch_url_source, def fetch_url_source_with_paste, def _semantic_scholar, def _pick_author_id, def _google_cse, def _duckduckgo_html, def _extract_publisher, _SLOT_QUERIES, def _search_web, def targeted_slot_search, def _find_institution_url, def fetch_institution_sources
- `engine/researcher_ids.py` — HEADERS, OA_HEADERS, _ORCID_RE, _SCHOLAR_RE, _SCOPUS_RE, _SD_AUTHOR_RE, _RESEARCHGATE_RE, _S2_AUTHOR_RE, _SD_PII_RE, def extract_ids_from_sources, def search_researcher_ids, def validate_orcid, def fetch_orcid_works, def extract_sd_pii, def is_sd_article_url, def is_sd_author_url, def resolve_sd_article, def find_openalex_id_for_person, def fetch_openalex_works, def fetch_s2_author_papers
- `engine/suggester.py` — _SLOT_PRIORITY, _PAYWALLED, _NEEDS_BROWSER, def _fetchability, def is_profile_url, def _classify_source_type, def _relevance, def _completion_value, def _extract_first_year, def detect_timeline_gaps, _SYSTEM, def _normalize_url, def suggest_next_urls
### frontend/
- `frontend/src/App.tsx` — ErrorBoundaryProps, ErrorBoundaryState, ErrorBoundary, constructor, getDerivedStateFromError, componentDidCatch, render, Stage, MainApp, handleMessage, handleConfirmed, handleResearchDone, handleDraft, handleReset, App
- `frontend/src/api.ts` — apiPost, apiGet, apiDelete, IdentifyResult, identifyPerson, startResearch, getSession, addSource, fetchFromBrowser, skipSuggestion, addSourcePaste, deepCrawl, verifyClaim, verifySource, rejectSource, generateDraft, SessionSummary, listSessions, resumeSession, deleteSession, TargetedSearchResponse, addDocumentFact, targetedSearch, ResearcherIdsResponse, findResearcherIds, RefreshPapersResponse, refreshPapers, suggestUrls
- `frontend/src/components/BookmarkletCard.tsx` — BookmarkletCard, handleCopy
- `frontend/src/components/CandidateCard.tsx` — Props, CandidateCard
- `frontend/src/components/ResearchOperationsCard.tsx` — ResearchOperationsCard
- `frontend/src/components/TimelineTab.tsx` — parseFirstYear, TimelineTab, TLEvent, GapInfo, EventRow, GapRow, handleFillGap
- `frontend/src/components/WorkspaceStatusBanner.tsx` — WorkspaceStatusBanner
- `frontend/src/pages/DraftPage.tsx` — Props, DraftPage, handleCopy, TabBtn, SourceRow
- `frontend/src/pages/HubPage.tsx` — Props, Tab, HubPage, handleGenerateDraft, markLinkOpened, SourceCategory, categorizeSource, SourcesPanel, handleAddUrl, handleAddPaste, handleCrawl, handleFetchFromBrowser, handleFindIds, handleRefreshPapers, viewInBrowser, SourceCard, handleVerify, handleReject, FillMode, ProfileTab, setMode, handleSearch, handleManual, ClaimsSection, doVerify, ActionBtn, ResearcherIdsStrip, RelevanceBadge, FetchedByTag, AuthorMatchBadge, Expander, NotabilityBadge, NotabilityCard, ChecklistCard, TabBtn
- `frontend/src/pages/IdentifyPage.tsx` — Props, View, IdentifyPage, handleResume, handleDelete, handleSearch, handleConfirm
- `frontend/src/pages/ResearchPage.tsx` — Props, ResearchPage, Spinner
- `frontend/src/types.ts` — PersonCandidate, SourceReliability, VerificationState, SourceFetchedBy, Source, Claim, NotabilityResult, WikiStatus, PersonProfile, ResearchStartResponse, SdPipelineResult, AddSourceResponse, AddSourcePasteResponse, CrawlResponse, DraftResponse, UrlSuggestion
- `frontend/src/url.ts` — normalizeUrl, getHostname
- `frontend/src/workflow.ts` — WorkspaceMode, WorkspaceTone, WorkspaceRoute, getWorkspaceRoute, canGenerateDraft, getDraftDestination
### tests/
- `tests/test_provenance.py` — def test_domain_trust_classification, def test_source_provenance_classification, def test_claim_trust_evaluation, def test_strict_notability_independence
- `tests/test_subject_routing.py` — class WikiStatusRoutingTests(test_existing_article_takes_precedence, test_existing_draft_routes_to_improvement, test_prior_deletion_routes_to_review, test_only_new_and_existing_draft_modes_can_generate_wikitext), class WikidataEnrichmentTests(test_invalid_qid_never_triggers_enrichment, test_confirmed_qid_can_supply_photo)
### wiki/
- `wiki/wiki_check.py` — HEADERS, WIKI_API, class WikiStatus, def draft_generation_allowed, def check_existing_page, def _page_exists, def _deletion_note
- `wiki/wikitext.py` — SYSTEM_EN, SYSTEM_HI, def render_en, def render_hi, def _build_prompt, def _commons_filename
