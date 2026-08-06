<!-- context-kit CODE_MAP · v0.1.0 · generated 2026-08-06 20:24 UTC · sha 3a0cbc4 · host vnic-trading -->

# CODE_MAP

Symbol index (skim-grade). Consult before Grep/Read.

## Composition
- Python — 39 files · 359 symbols
- TypeScript — 21 files · 142 symbols
- JavaScript — 1 files · 0 symbols
- CSS — 1 file (unindexed)
- HTML — 1 file (unindexed)
- Shell Script — 1 file (unindexed)
_Total: 64 files · 501 symbols across 6 languages._


## Compartments
- `auto` — dynamic (git files in play + 2-hop import neighborhood)

Run `ck compartment <name>` to load a compartment's warm symbol index.

### ./
- `browser_server.py` — PROFILE_DIR, XVFB_DISPLAY, PORT, class _Cmd, _q, _headed, _running, _xvfb, def _dispatch, def _try_start_xvfb, def _browser_thread, def lifespan, app, def screenshot, class NavReq, def navigate, def info, class ViewportReq, def set_viewport, class ClickReq, def click, class TypeReq, def type_text, class KeyReq, def press_key, class ScrollReq, def scroll, def go_back, def go_forward, def reload, def get_content, def status, def index, BROWSER_HTML, def start_browser, def stop_browser
- `generate_draft.py` — session_file, data, profile, audit, wikitext, out_en
### backend/
- `backend/main.py` — api_app, def lifespan, app, FRONTEND_DIST
- `backend/pipelines.py` — def _add_sd_article, def _add_sd_author_profile
- `backend/routes.py` — router, def identify, def research_start, def add_source, def add_document_fact, def add_sourced_claim, def verify_claim, def add_source_paste, def deep_crawl, def targeted_search_endpoint, def auto_enrich_endpoint, def draft_audit, def generate_draft, def get_session, def verify_source, def reject_source, def list_sessions, def delete_session, def find_researcher_ids_endpoint, def refresh_papers_endpoint, def fetch_from_browser, def suggest_urls
- `backend/routes_sessions.py` — sessions_router, def resume_session
- `backend/schemas.py` — class IdentifyRequest, class ResearchRequest, class AddSourceRequest, class AddDocumentFact, class AddSourcedClaimRequest, class VerifyClaimRequest, class AddSourcePaste, class CrawlRequest, class TargetedSearchRequest, class DraftRequest, class FindIdsRequest, class RefreshPapersRequest
- `backend/store.py` — SESSIONS_DIR, _sessions, _wiki_statuses, _llm, def llm, def _session_path, def _apply_provenance, def _save_session, def _load_session_file, BROWSER_SERVER, def _push_to_browser, def _get_profile, def _check_doi_sources
### engine/
- `engine/agent_llm.py` — AGENT_JOBS_DIR, def _job_id, class AgentProvider(__init__, complete), def pending_jobs, def answer_job
- `engine/author_check.py` — CROSSREF_API, TIMEOUT, def name_variants, def _normalise, def _author_matches_variants, def _affiliation_matches, def check_doi_authors, def extract_doi
- `engine/classifier.py` — _RS_DOMAINS, _PRIMARY_DOMAINS, _SELF_DOMAINS, _UNRELIABLE_DOMAINS, def _domain_classify, SYSTEM, def classify_sources
- `engine/crawler.py` — TIMEOUT, S2_API, class SourceNode, class SourceGraph(to_sources), def crawl, def _extract_meta, def _extract_links, def _extract_dois, def _extract_entities, def _count_mentions, def _is_relevant_link, def _entity_worth_searching, def _search_entity, def _temporal_variants, def _expand_doi
- `engine/extractor.py` — WIKI_SLOTS, SLOT_SOURCE_HINTS, def find_missing_slots, SYSTEM, def _validate_and_filter_claims, def filter_person_snippets, def extract_claims, def _deduplicate
- `engine/fetcher.py` — HEADERS, BOT_HEADERS, TIMEOUT, def check_liveness, def get_wayback_url, class FetchResult(__init__), BROWSER_SERVER, def _try_browser_server, def fetch_url, def fetch_orcid_by_name, def fetch_text_paste, def _direct_fetch, def _pdf_extract, def _wayback_fetch, def _orcid_fetch, def _fetch_orcid_id, def _orcid_to_text, def _extract_text
- `engine/fetcher_browser.py` — _SESSION_DIR, _BLOCKED_SIGNALS, _LAUNCH_ARGS, _STEALTH_JS, _UA, def fetch_with_browser
- `engine/identifier.py` — HEADERS, WIKI_API, WIKIDATA_API, def fetch_wikidata_photo, def fetch_wikidata_photo_by_id, def find_candidates, _HONORIFICS, def _significant_tokens, def _name_matches, def _search_wikipedia, def _search_wikidata, def _wikipedia_detail, def _wikidata_detail, def _wikidata_image, def _looks_like_person, def _strip_html
- `engine/link_extractor.py` — _PROFILE_DOMAINS, _PROFILE_PATH_FRAGMENTS, def extract_profile_links
- `engine/llm.py` — class LLMProvider(complete), class ClaudeProvider(__init__, complete), class GeminiProvider(__init__, complete), class VertexClaudeProvider(__init__, complete), class LocalProvider(complete), class NullProvider(complete), class StubProvider(complete, _classify, _extract), _stub_warned, _agent_warned, def _agent_provider, def _warn_agent_mode, def has_real_llm, def _stub_provider, def get_provider
- `engine/models.py` — class SourceReliability, class VerificationState, class Source, class Claim, class NotabilityResult, class PersonCandidate, class PersonProfile
- `engine/notability.py` — S2_API, def score_notability, def _semantic_scholar_signals
- `engine/provenance.py` — def normalize_url, HIGH_TRUST_DOMAINS, MEDIUM_TRUST_DOMAINS, UNTRUSTED_DOMAINS, RECORD_REGISTRY_DOMAINS, def get_domain_trust, def classify_source_provenance, def evaluate_claim_trust
- `engine/relevance.py` — _WRONG_PERSON_SIGNALS, _ACADEMIC_FETCHED_BY, _DOI_PATTERNS, def _significant_name_tokens, def flag_source, def flag_sources
- `engine/researcher.py` — HEADERS, S2_API, GOOGLE_CSE_URL, _NEWS_OUTLETS, _DISAMBIG_STOPWORDS, def _disambiguator, def _sweep_news, def fetch_auto_sources, def fetch_url_source, def fetch_url_source_with_paste, def _semantic_scholar, def _pick_author_id, def _google_cse, def _duckduckgo_html, def _extract_publisher, _SLOT_QUERIES, def _search_web, def targeted_slot_search, def _find_institution_url, def fetch_institution_sources
- `engine/researcher_ids.py` — HEADERS, OA_HEADERS, _ORCID_RE, _SCHOLAR_RE, _SCOPUS_RE, _SD_AUTHOR_RE, _RESEARCHGATE_RE, _S2_AUTHOR_RE, _SD_PII_RE, def extract_ids_from_sources, def search_researcher_ids, def validate_orcid, def fetch_orcid_works, def extract_sd_pii, def is_sd_article_url, def is_sd_author_url, def resolve_sd_article, def find_openalex_id_for_person, def fetch_openalex_works, def fetch_s2_author_papers
- `engine/suggester.py` — _SLOT_PRIORITY, _PAYWALLED, _NEEDS_BROWSER, def _fetchability, def is_profile_url, def _classify_source_type, def _relevance, def _completion_value, def _extract_first_year, def detect_timeline_gaps, _SYSTEM, def _normalize_url, def _generate_multiyear_report_urls, def _profile_link_suggestions, def _multiyear_report_suggestions, def _build_search_prompt, def _search_queries, def _run_search_queries, def suggest_next_urls
### frontend/
- `frontend/src/App.tsx` — ErrorBoundaryProps, ErrorBoundaryState, ErrorBoundary, constructor, getDerivedStateFromError, componentDidCatch, render, Stage, MainApp, handleMessage, handleConfirmed, handleResearchDone, handleDraft, handleReset, App
- `frontend/src/api.ts` — apiPost, apiGet, apiDelete, IdentifyResult, identifyPerson, startResearch, getSession, addSource, fetchFromBrowser, skipSuggestion, addSourcePaste, deepCrawl, verifyClaim, verifySource, rejectSource, getDraftAudit, generateDraft, SessionSummary, listSessions, resumeSession, deleteSession, TargetedSearchResponse, addDocumentFact, addSourcedClaim, targetedSearch, ResearcherIdsResponse, findResearcherIds, RefreshPapersResponse, refreshPapers, suggestUrls, AutoEnrichResponse, autoEnrich
- `frontend/src/components/BookmarkletCard.tsx` — BookmarkletCard, handleCopy
- `frontend/src/components/CandidateCard.tsx` — Props, CandidateCard
- `frontend/src/components/ClaimsReview.tsx` — FilterTab, ClaimsReview, doVerify, ActionBtn
- `frontend/src/components/ProfileTab.tsx` — ProfileTab, setMode, handleSearch, handleAddUrl, handleManual, ResearcherIdsStrip
- `frontend/src/components/ResearchOperationsCard.tsx` — ResearchOperationsCard
- `frontend/src/components/SourceCard.tsx` — SourceCard, handleVerify, handleReject, FillMode, RelevanceBadge, FetchedByTag, AuthorMatchBadge
- `frontend/src/components/SourcesPanel.tsx` — SourceCategory, categorizeSource, SourcesPanel, loadSuggestions, handleApproveSuggestion, handleAddUrl, handleAddPaste, handleCrawl, handleFetchFromBrowser, handleFindIds, handleRefreshPapers, viewInBrowser
- `frontend/src/components/TimelineTab.tsx` — parseFirstYear, TimelineTab, TLEvent, GapInfo, EventRow, GapRow, handleFillGap
- `frontend/src/components/WorkspaceCards.tsx` — Expander, NotabilityBadge, NotabilityCard, DraftReadinessCard, ChecklistCard, TabBtn
- `frontend/src/components/WorkspaceStatusBanner.tsx` — WorkspaceStatusBanner
- `frontend/src/pages/DraftPage.tsx` — Props, DraftPage, handleCopy, TabBtn, SourceRow
- `frontend/src/pages/HubPage.tsx` — Props, Tab, HubPage, handleAutoEnrich, handleGenerateDraft, markLinkOpened
- `frontend/src/pages/IdentifyPage.tsx` — Props, View, IdentifyPage, handleResume, handleDelete, handleSearch, handleConfirm
- `frontend/src/pages/ResearchPage.tsx` — Props, ResearchPage, Spinner
- `frontend/src/types.ts` — PersonCandidate, SourceReliability, VerificationState, SourceFetchedBy, Source, Claim, NotabilityResult, WikiStatus, PersonProfile, ResearchStartResponse, SdPipelineResult, AddSourceResponse, AddSourcePasteResponse, CrawlResponse, DraftIssue, DraftAudit, DraftResponse, UrlSuggestion
- `frontend/src/url.ts` — normalizeUrl, getHostname
- `frontend/src/workflow.ts` — WorkspaceMode, WorkspaceTone, WorkspaceRoute, getWorkspaceRoute, canGenerateDraft, getDraftDestination
### tests/
- `tests/test_agent_llm.py` — def test_unanswered_prompt_queues_job_and_returns_empty, def test_answered_prompt_returns_agent_response, def test_get_provider_selects_agent_via_env
- `tests/test_draft.py` — def _source, def _ready_profile, def test_audit_excludes_cv_animal_birth_and_unverified_sources, def test_audit_blocks_profiles_without_explicit_draft_approval, def test_audit_blocks_drafts_without_independent_secondary_coverage, def test_renderer_cites_every_included_claim_and_never_fills_biography_gaps, def test_dr_yadav_saved_session_produces_policy_filtered_draft, def test_audit_accepts_sourced_research_stay_as_career_activity, def test_claim_draft_approval_is_a_separate_persisted_action, def test_draft_endpoint_uses_server_session_and_persists_output, def test_add_sourced_claim_binds_fact_to_verified_source, def test_add_sourced_claim_requires_existing_source, def test_resume_never_repopulates_claims_from_stub_provider, def test_independent_count_uses_distinct_outlets_not_article_urls, def test_verified_amar_ujala_report_counts_as_independent_news
- `tests/test_liveness.py` — def test_check_liveness_live, def test_check_liveness_dead_looks_up_wayback, def test_check_liveness_blocked, def test_get_wayback_url_parses_snapshot, def test_audit_excludes_dead_unarchived_source, def test_renderer_cites_wayback_url_for_dead_archived_source
- `tests/test_llm.py` — def test_extract_claims_is_noop_under_stub, def test_get_provider_uses_vertex_when_available, def test_get_provider_falls_back_to_agent_when_vertex_unavailable
- `tests/test_provenance.py` — def test_domain_trust_classification, def test_source_provenance_classification, def test_claim_trust_evaluation, def test_strict_notability_independence, def test_icar_and_cirb_reports_are_institutional_primary_sources, def test_record_registries_are_primary_and_non_independent
- `tests/test_researcher.py` — def _result, def test_disambiguator_drops_institutional_stopwords, def test_news_sweep_issues_site_restricted_and_hindi_queries, def test_news_sweep_deduplicates_across_queries, def test_news_sweep_respects_limit
- `tests/test_researcher_ids.py` — def _profile, def test_find_ids_removes_an_orcid_that_fails_identity_validation, def test_refresh_rejects_an_unvalidated_orcid
- `tests/test_subject_routing.py` — class WikiStatusRoutingTests(test_existing_article_takes_precedence, test_existing_draft_routes_to_improvement, test_prior_deletion_routes_to_review, test_only_new_and_existing_draft_modes_can_generate_wikitext), class WikidataEnrichmentTests(test_invalid_qid_never_triggers_enrichment, test_confirmed_qid_can_supply_photo)
- `tests/test_suggester.py` — def test_multiyear_sweep_never_fabricates_dois_or_publisher_urls, def test_multiyear_sweep_still_covers_institutional_report_series, def test_report_guesses_are_bounded_and_real_searches_still_rank
### wiki/
- `wiki/draft.py` — class DraftIssue, class DraftEvidence, class DraftAudit, _NOISE_PATTERNS, _ROLE_WORDS, _CAREER_ACTIVITY_WORDS, _INSTITUTION_WORDS, _PUBLICATION_WORDS, _BIRTH_SUBJECT_NOISE, _PRIMARY_OR_PROFILE_DOMAINS, _INDEPENDENT_NEWS_DOMAINS, def _host, def _is_independent_secondary, def _source_rank, def _claim_exclusion, def audit_profile, def _clean, def _display_name, def _cite_value, def _ref_name, def _citation, def _items_for, def _claim_text, def _item_year, def _render_items, def render_draft
- `wiki/wiki_check.py` — HEADERS, WIKI_API, class WikiStatus, def draft_generation_allowed, def check_existing_page, def _page_exists, def _deletion_note
