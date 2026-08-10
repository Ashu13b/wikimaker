export interface PersonCandidate {
  name: string;
  photo_url: string | null;
  bio_snippet: string;
  birth_year: string | null;
  nationality: string | null;
  field: string | null;
  affiliation: string | null;
  wikipedia_url: string | null;
  wikidata_id: string | null;
}

export type SourceReliability = "reliable_secondary" | "primary" | "self_published" | "unreliable";
export type VerificationState = "unverified" | "confirmed" | "edited" | "skipped";
export type SourceFetchedBy = "semantic_scholar" | "google_search" | "duckduckgo" | "crawl" | "user" | "openalex" | "orcid" | "browser" | null;

export interface Source {
  url: string;
  coverage_depth: "unassessed" | "passing_mention" | "significant";
  editorial_origin: string | null;
  research_notes: string;
  title: string;
  publisher: string;
  reliability: SourceReliability;
  snippet: string;
  date: string | null;
  user_provided: boolean;
  human_verified: boolean;
  is_independent?: boolean;
  domain_trust?: "high" | "medium" | "low" | "untrusted";
  provenance_category?: "independent_secondary" | "authored_publication" | "institutional_bio" | "self_published" | "general_web";
  fetched_by: SourceFetchedBy;
  author_match_status: "confirmed" | "possible" | "wrong_person" | "not_found" | "no_data" | null;
  author_match_name: string | null;
  author_match_affiliation: string | null;
  all_paper_authors: string[];
  relevance_flag: "relevant" | "uncertain" | "likely_wrong" | "unscored";
  redirected_to: string | null;
  liveness?: "alive" | "blocked" | "dead" | "unknown";
  archive_url?: string | null;
  profile_links: string[];
}

export interface Claim {
  text: string;
  field: string;
  source_url: string | null;
  verification: VerificationState;
  user_provided: boolean;
  auto_source_attempted: boolean;
  date_context?: string | null;
  draft_approved?: boolean;
  draft_text?: string | null;
  trust_score?: number;
  provenance_status?: "verified_independent" | "primary_sourced" | "unverified";
  is_independent?: boolean;
}

export interface NotabilityResult {
  score: number;
  label: string;
  rs_count: number;
  candidate_count: number;
  reason: string;
  passed: boolean;
}

export interface WikiStatus {
  status: "exists" | "draft" | "deleted" | "clear";
  url: string | null;
  note: string | null;
}

export interface PersonProfile {
  name: string;
  wikidata_id: string | null;
  wikipedia_url: string | null;
  photo_url: string | null;
  full_name: string | null;
  birth_date: string | null;
  birth_place: string | null;
  nationality: string | null;
  field: string | null;
  affiliation: string | null;
  known_for: string | null;
  awards: string[];
  sources: Source[];
  claims: Claim[];
  skipped_sources: string[];
  rejected_sources: string[];
  missing_slots: string[];
  researcher_ids: Record<string, string>;
  confirmed_ids: Record<string, boolean>;
  notability: NotabilityResult | null;
  wikitext_en: string | null;
  wikitext_hi: string | null;
}

// Response shapes matching FastAPI endpoints
export interface ResearchStartResponse {
  wiki_status: WikiStatus;
  notability: NotabilityResult;
  profile: PersonProfile;
  resumed?: boolean;
}

export interface SdPipelineResult {
  doi?: string;
  title?: string;
  crossref_authors?: string[];
  openalex_author_id?: string | null;
  openalex_works_added?: number;
  scopus_id?: string | null;
}

export interface AddSourceResponse {
  source: Source | null;
  blocked: boolean;
  new_claims: Claim[];
  notability: NotabilityResult;
  pipeline?: SdPipelineResult | null;
  researcher_ids?: Record<string, string>;
  confirmed_ids?: Record<string, boolean>;
  sent_to_browser?: boolean;
}

export interface AddSourcePasteResponse {
  source: Source;
  new_claims: Claim[];
  notability: NotabilityResult;
}

export interface CrawlResponse {
  nodes_crawled: number;
  relevant_sources: number;
  new_claims: number;
  notability: NotabilityResult;
  sources: Source[];
}

export interface DraftIssue {
  code: string;
  message: string;
  count: number;
}

export interface DraftAudit {
  ready: boolean;
  eligible_claim_count: number;
  eligible_source_count: number;
  independent_source_count: number;
  excluded_claim_count: number;
  blockers: DraftIssue[];
  warnings: DraftIssue[];
  exclusions: DraftIssue[];
}

export interface DraftResponse {
  profile: PersonProfile;
  audit: DraftAudit;
}

export type DraftLinkStatus = "ok" | "blocked" | "dead" | "unknown";

export interface DraftLink {
  url: string;
  label: string;
  archived: boolean;
  status: DraftLinkStatus;
  status_code: number | null;
  final_url: string | null;
}

export type DraftQaSeverity = "error" | "warning" | "info";

export interface DraftQaFinding {
  id: string;
  severity: DraftQaSeverity;
  message: string;
}

export interface DraftQaReport {
  findings: DraftQaFinding[];
  passed: boolean;
  counts: Record<DraftQaSeverity, number>;
}

export interface UrlSuggestion {
  url: string;
  title: string;
  snippet: string;
  reason: string;
  query?: string;
  expected_slots: string[];
  priority: number;
  source_type?: "profile" | "publication" | "news";
  fetchable: "open" | "needs_browser" | "paywalled";
  relevance: "high" | "medium" | "low";
  completion_value: number;
}

