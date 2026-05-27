import type {
  PersonCandidate,
  PersonProfile,
  ResearchStartResponse,
  AddSourceResponse,
  AddSourcePasteResponse,
  CrawlResponse,
  DraftResponse,
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
  title: string;
  url: string;
  snippet: string;
  publisher: string;
}

export async function identifyPerson(
  name: string, field: string | null, affiliation: string | null
): Promise<IdentifyResult[]> {
  const data = await apiPost<{ results: IdentifyResult[] }>("/identify", { name, field, affiliation });
  return data.results;
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
  action: "confirm" | "edit" | "skip",
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

export async function rejectSource(
  profileName: string,
  url: string,
  reason: string,
): Promise<{ removed_claim_count: number; sources: import("./types").Source[]; claims: import("./types").Claim[]; notability: import("./types").NotabilityResult }> {
  return apiPost("/research/source/reject", { profile_name: profileName, url, reason });
}

export async function generateDraft(
  profile: PersonProfile,
  generateHindi: boolean,
): Promise<DraftResponse> {
  return apiPost("/draft", { profile, generate_hindi: generateHindi });
}

export interface SessionSummary {
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

export async function listSessions(): Promise<SessionSummary[]> {
  const data = await apiGet<{ sessions: SessionSummary[] }>("/sessions");
  return data.sessions;
}

export async function resumeSession(file: string): Promise<{ profile: PersonProfile; wiki_status: import("./types").WikiStatus }> {
  return apiPost("/sessions/resume", { file });
}

export async function deleteSession(file: string): Promise<void> {
  await apiDelete(`/sessions/${encodeURIComponent(file)}`);
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
