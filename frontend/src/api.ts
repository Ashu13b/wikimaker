import type {
  PersonCandidate,
  PersonProfile,
  ResearchStartResponse,
  AddSourceResponse,
  AddSourcePasteResponse,
  CrawlResponse,
  DraftResponse,
  DraftAudit,
  NotabilityResult,
} from "./types";

// Configurable for mobile builds (set VITE_API_BASE env var to the device's server IP)
const BASE = (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE) ?? "/api";

async function apiPost<T>(path: string, body: unknown, params?: Record<string, string>): Promise<T> {
  const url = params
    ? `${BASE}${path}?${new URLSearchParams(params).toString()}`
    : `${BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface IdentifyResult {
  kind: "identity" | "web";
  title: string;
  url: string;
  snippet: string;
  publisher: string;
  wikidata_id?: string | null;
  wikipedia_url?: string | null;
  photo_url?: string | null;
  birth_year?: string | null;
  nationality?: string | null;
  field?: string | null;
  affiliation?: string | null;
}

export async function identifyPerson(
  name: string, field: string | null, affiliation: string | null
): Promise<{ results: IdentifyResult[]; wiki_status: import("./types").WikiStatus | null }> {
  const data = await apiPost<{ results: IdentifyResult[]; wiki_status: import("./types").WikiStatus | null }>(
    "/identify", { name, field, affiliation });
  return data;
}

export async function startResearch(
  candidate: PersonCandidate,
): Promise<ResearchStartResponse> {
  return apiPost("/research/start", {
    name: candidate.name,
    wikidata_id: candidate.wikidata_id,
    wikipedia_url: candidate.wikipedia_url,
    photo_url: candidate.photo_url,
    field: candidate.field,
    affiliation: candidate.affiliation,
    nationality: candidate.nationality,
    birth_year: candidate.birth_year,
  });
}

export async function getSession(name: string): Promise<PersonProfile> {
  const data = await apiGet<{ profile: PersonProfile }>(`/session/${encodeURIComponent(name)}`);
  return data.profile;
}

export async function addSource(profileName: string, url: string): Promise<AddSourceResponse> {
  return apiPost("/research/add-source", { profile_name: profileName, url });
}

export async function fetchFromBrowser(profileName: string): Promise<AddSourceResponse> {
  return apiPost("/research/fetch-from-browser", { profile_name: profileName });
}

export async function fetchBlockedSources(profileName: string): Promise<{
  fetched: string[];
  walls: string[];
  profile?: PersonProfile;
  notability?: NotabilityResult | null;
}> {
  return apiPost("/research/fetch-blocked", { profile_name: profileName });
}

export async function skipSuggestion(profileName: string, url: string): Promise<{ ok: boolean }> {
  return apiPost("/research/skip-suggestion", { profile_name: profileName, url });
}

export async function addSourcePaste(
  profileName: string,
  url: string,
  pastedText: string,
): Promise<AddSourcePasteResponse> {
  return apiPost("/research/add-source-paste", {
    profile_name: profileName,
    url,
    pasted_text: pastedText,
  });
}

export async function deepCrawl(
  profileName: string,
  seedUrls: string[],
  keywords: string[],
  maxNodes = 40,
  maxDepth = 3,
): Promise<CrawlResponse> {
  return apiPost("/research/crawl", {
    profile_name: profileName,
    seed_urls: seedUrls,
    keywords,
    max_nodes: maxNodes,
    max_depth: maxDepth,
  });
}

export async function verifyClaim(
  profileName: string,
  claimIndex: number,
  action: "confirm" | "edit" | "skip" | "approve_draft" | "remove_draft",
  editedText?: string,
): Promise<{ claim: import("./types").Claim }> {
  return apiPost(
    "/research/verify-claim",
    { claim_index: claimIndex, action, edited_text: editedText ?? null },
    { name: profileName },
  );
}

export async function verifySource(
  profileName: string,
  url: string,
  verified: boolean,
): Promise<{ new_claims: import("./types").Claim[]; missing_slots: string[]; notability: import("./types").NotabilityResult | null }> {
  return apiPost("/research/source/verify", { profile_name: profileName, url, verified });
}

export async function assessSource(
  profileName: string,
  url: string,
  coverageDepth: import("./types").Source["coverage_depth"],
  editorialOrigin: string,
  researchNotes: string,
): Promise<{ source: import("./types").Source; notability: NotabilityResult | null }> {
  return apiPost("/research/source/assess", {
    profile_name: profileName,
    url, coverage_depth: coverageDepth,
    editorial_origin: editorialOrigin || null,
    research_notes: researchNotes,
  });
}
export async function rejectSource(
  profileName: string,
  url: string,
  reason: string,
): Promise<{ removed_claim_count: number; sources: import("./types").Source[]; claims: import("./types").Claim[]; notability: import("./types").NotabilityResult }> {
  return apiPost("/research/source/reject", { profile_name: profileName, url, reason });
}

export async function getDraftAudit(profileName: string): Promise<DraftAudit> {
  const data = await apiGet<{ audit: DraftAudit }>(`/draft/audit/${encodeURIComponent(profileName)}`);
  return data.audit;
}

export async function getDraftLinks(profileName: string): Promise<import("./types").DraftLink[]> {
  const data = await apiPost<{ links: import("./types").DraftLink[] }>("/draft/links", { profile_name: profileName });
  return data.links;
}

export async function getDraftPreview(profileName: string): Promise<string> {
  const data = await apiPost<{ html: string }>("/draft/preview", { profile_name: profileName });
  return data.html;
}

export async function getDraftQa(profileName: string): Promise<import("./types").DraftQaReport> {
  return apiPost("/draft/qa", { profile_name: profileName });
}

export async function generateDraft(profileName: string): Promise<DraftResponse> {
  return apiPost("/draft", { profile_name: profileName });
}

export interface ClaimCoverage {
  claim_index: number;
  field: string;
  text: string;
  date_context: string | null;
  source_url: string | null;
  covered: boolean;
  score: number;
  note: string;
}

export interface ArticleProposal {
  article_title: string;
  article_url: string;
  article_excerpt: string;
  covered_count: number;
  missing_count: number;
  coverage: ClaimCoverage[];
}

export async function getArticleProposal(profileName: string): Promise<ArticleProposal> {
  const data = await apiPost<{ proposal: ArticleProposal }>("/research/article-proposal", { profile_name: profileName });
  return data.proposal;
}

export interface SessionSummary {
  id: string | null;
  name: string;
  field: string | null;
  affiliation: string | null;
  photo_url: string | null;
  source_count: number;
  claim_count: number;
  notability_label: string;
  notability_score: number;
  saved_at: string | null;
  file: string;
}

/** Stable session reference: the immutable session id when present, else the name. */
export function profileRef(profile: { session_id?: string | null; name: string }): string {
  return profile.session_id ?? profile.name;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const data = await apiGet<{ sessions: SessionSummary[] }>("/sessions");
  return data.sessions;
}

export async function resumeSession(ref: string): Promise<{ profile: PersonProfile; wiki_status: import("./types").WikiStatus }> {
  return apiPost("/sessions/resume", { file: ref, session_id: ref });
}

export async function deleteSession(ref: string): Promise<void> {
  await apiDelete(`/sessions/${encodeURIComponent(ref)}`);
}

export interface TargetedSearchResponse {
  sources: import("./types").Source[];
  new_claims: import("./types").Claim[];
  missing_slots: string[];
  notability: import("./types").NotabilityResult;
}

export async function addDocumentFact(
  profileName: string,
  field: string,
  text: string,
): Promise<{ claim: import("./types").Claim }> {
  return apiPost("/research/add-document-fact", { profile_name: profileName, field, text });
}

export async function targetedSearch(
  profileName: string,
  slot: string,
  hint?: string,
): Promise<TargetedSearchResponse> {
  return apiPost("/research/targeted-search", {
    profile_name: profileName,
    slot,
    hint: hint ?? null,
  });
}

export interface ResearcherIdsResponse {
  researcher_ids: Record<string, string>;
  confirmed_ids: Record<string, boolean>;
}

export async function findResearcherIds(profileName: string): Promise<ResearcherIdsResponse> {
  return apiPost("/research/find-researcher-ids", { profile_name: profileName });
}

export interface RefreshPapersResponse {
  new_source_count: number;
  new_claim_count: number;
  sources: import("./types").Source[];
  claims: import("./types").Claim[];
  notability: import("./types").NotabilityResult;
  researcher_ids: Record<string, string>;
  confirmed_ids: Record<string, boolean>;
}

export async function refreshPapers(
  profileName: string,
  idType: string,
  idValue: string,
  confirm?: boolean,
): Promise<RefreshPapersResponse> {
  return apiPost("/research/refresh-papers", {
    profile_name: profileName,
    id_type: idType,
    id_value: idValue,
    confirm: confirm ?? false,
  });
}

export async function suggestUrls(profileName: string): Promise<import("./types").UrlSuggestion[]> {
  const data = await apiPost<{ suggestions: import("./types").UrlSuggestion[] }>("/research/suggest", { profile_name: profileName });
  return data.suggestions;
}

export interface AutoEnrichResponse {
  ok: boolean;
  added_source_count: number;
  added_claim_count: number;
  missing_slots: string[];
  notability: import("./types").NotabilityResult;
}

export async function autoEnrich(profileName: string): Promise<AutoEnrichResponse> {
  return apiPost("/research/auto-enrich", { profile_name: profileName });
}
