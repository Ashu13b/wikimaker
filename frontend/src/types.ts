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
export type SourceFetchedBy = "semantic_scholar" | "google_search" | "duckduckgo" | "crawl" | "user" | "openalex" | "orcid" | null;

export interface Source {
  url: string;
  title: string;
  publisher: string;
  reliability: SourceReliability;
  snippet: string;
  date: string | null;
  user_provided: boolean;
  human_verified: boolean;
  fetched_by: SourceFetchedBy;
  author_match_status: "confirmed" | "possible" | "wrong_person" | "not_found" | "no_data" | null;
  author_match_name: string | null;
  author_match_affiliation: string | null;
  all_paper_authors: string[];
  relevance_flag: "relevant" | "uncertain" | "likely_wrong" | "unscored";
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
}

export interface NotabilityResult {
  score: number;
  label: string;
  rs_count: number;
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

export interface DraftResponse {
  profile: PersonProfile;
}

export interface UrlSuggestion {
  url: string;
  title: string;
  snippet: string;
  reason: string;
  query?: string;
  expected_slots: string[];
  priority: number;
  fetchable: "open" | "needs_browser" | "paywalled";
  relevance: "high" | "medium" | "low";
  completion_value: number;
}

