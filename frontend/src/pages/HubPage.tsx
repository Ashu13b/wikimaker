import { useState, useEffect } from "react";
import type { PersonProfile, WikiStatus, Source, Claim, NotabilityResult } from "../types";
import { addSource, addSourcePaste, deepCrawl, verifyClaim, verifySource, rejectSource, generateDraft, getSession, targetedSearch, addDocumentFact, findResearcherIds, refreshPapers, fetchFromBrowser, suggestUrls } from "../api";
import type { UrlSuggestion } from "../types";

interface Props {
  initialProfile: PersonProfile;
  wikiStatus: WikiStatus;
  generateHindi: boolean;
  onDraft: (profile: PersonProfile) => void;
  onReset: () => void;
  relayPending?: { url: string; text: string } | null;
  onRelayConsumed?: () => void;
}

type Tab = "sources" | "profile" | "timeline" | "pending";

export default function HubPage({ initialProfile, wikiStatus, generateHindi, onDraft, onReset, relayPending, onRelayConsumed }: Props) {
  const [profile, setProfile] = useState(initialProfile);
  const [tab, setTab] = useState<Tab>("sources");
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  // Track which source links the user has opened (session-local, not persisted)
  const [openedLinks, setOpenedLinks] = useState<Set<string>>(new Set());

  // Switch to sources tab when Wiki+ relay content arrives
  useEffect(() => {
    if (relayPending) setTab("sources");
  }, [relayPending]);

  async function handleGenerateDraft() {
    setDrafting(true);
    setDraftError(null);
    try {
      const result = await generateDraft(profile, generateHindi);
      onDraft(result.profile);
    } catch (e) {
      setDraftError(String(e));
    } finally {
      setDrafting(false);
    }
  }

  function markLinkOpened(url: string) {
    setOpenedLinks(prev => new Set(prev).add(url));
  }

  const pendingClaims = profile.claims.filter(c => c.verification === "unverified");
  const skippedClaims = profile.claims.filter(c => c.verification === "skipped");

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "20px 20px 60px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20, gap: 16, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {profile.photo_url ? (
            <img src={profile.photo_url} alt={profile.name}
              style={{ width: 52, height: 52, borderRadius: 8, objectFit: "cover", border: "1px solid var(--border)" }} />
          ) : (
            <div style={{
              width: 52, height: 52, borderRadius: 8, background: "var(--primary)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 22, fontWeight: 800, color: "#fff", flexShrink: 0,
            }}>
              {profile.name[0]}
            </div>
          )}
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 2 }}>{profile.name}</h1>
            <p style={{ fontSize: 13, color: "var(--muted)" }}>
              {[profile.field, profile.affiliation, profile.nationality].filter(Boolean).join(" · ")}
            </p>
            {profile.notability && <NotabilityBadge n={profile.notability} />}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button className="btn-ghost" onClick={onReset} style={{ fontSize: 13 }}>New search</button>
          <button className="btn-primary" onClick={handleGenerateDraft} disabled={drafting}>
            {drafting ? "Generating…" : "Generate draft →"}
          </button>
        </div>
      </div>

      {draftError && (
        <div style={{ background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontSize: 13, color: "var(--danger)" }}>
          {draftError}
        </div>
      )}

      {(wikiStatus.status === "deleted" || wikiStatus.status === "draft") && wikiStatus.note && (
        <div style={{ background: "#fef9c3", border: "1px solid #fde047", borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontSize: 13 }}>
          <strong>Note:</strong> {wikiStatus.note}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 272px", gap: 20, alignItems: "start" }}>
        {/* Main panel */}
        <div>
          {/* Tabs */}
          <div style={{ display: "flex", borderBottom: "1px solid var(--border)" }}>
            <TabBtn active={tab === "sources"} onClick={() => setTab("sources")}>
              Sources ({profile.sources.length})
            </TabBtn>
            <TabBtn active={tab === "profile"} onClick={() => setTab("profile")}>
              Wikipedia Profile
              {(profile.missing_slots ?? []).length > 0 && (
                <span style={{ marginLeft: 6, background: "var(--warning)", color: "#fff", borderRadius: 10, padding: "1px 7px", fontSize: 11 }}>
                  {(profile.missing_slots ?? []).length} missing
                </span>
              )}
            </TabBtn>
            <TabBtn active={tab === "timeline"} onClick={() => setTab("timeline")}>
              Timeline
            </TabBtn>
            <TabBtn active={tab === "pending"} onClick={() => setTab("pending")}>
              Review ({pendingClaims.length})
              {pendingClaims.length > 0 && (
                <span style={{ marginLeft: 6, background: "var(--primary)", color: "#fff", borderRadius: 10, padding: "1px 7px", fontSize: 11 }}>
                  {pendingClaims.length}
                </span>
              )}
            </TabBtn>
          </div>

          {tab === "sources" && (
            <SourcesPanel
              profile={profile}
              openedLinks={openedLinks}
              onLinkOpen={markLinkOpened}
              onProfileUpdate={setProfile}
              relayPending={relayPending}
              onRelayConsumed={onRelayConsumed}
            />
          )}
          {tab === "profile" && (
            <ProfileTab profile={profile} onProfileUpdate={setProfile} />
          )}
          {tab === "timeline" && (
            <TimelineTab profile={profile} />
          )}
          {tab === "pending" && (
            <ClaimsSection
              claims={[...pendingClaims, ...skippedClaims]}
              allClaims={profile.claims}
              profile={profile}
              onProfileUpdate={setProfile}
              emptyMessage="All claims have been reviewed."
            />
          )}
        </div>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {profile.notability && <NotabilityCard n={profile.notability} />}
          <ChecklistCard profile={profile} wikiStatus={wikiStatus} />
          <button className="btn-primary" onClick={handleGenerateDraft} disabled={drafting} style={{ width: "100%" }}>
            {drafting ? "Generating…" : "Generate draft →"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Shared tag constants ──────────────────────────────────────────────────────

const SOURCE_TAG_CLASS: Record<string, string> = {
  reliable_secondary: "tag-rs",
  primary: "tag-primary",
  self_published: "tag-self",
  unreliable: "tag-unreliable",
};
const SOURCE_TAG_LABEL: Record<string, string> = {
  reliable_secondary: "RS",
  primary: "Primary",
  self_published: "Self",
  unreliable: "Unreliable",
};

// ── Sources panel ──────────────────────────────────────────────────────────────

type SourceCategory = "research" | "news" | "profile";

function categorizeSource(s: Source): SourceCategory {
  const url = s.url.toLowerCase();
  // Research: academic databases, DOI, reliable secondary, scholar tools
  if (s.fetched_by === "semantic_scholar") return "research";
  if (s.reliability === "reliable_secondary") return "research";
  if (["doi.org","pubmed","ncbi.nlm","springer","plos","tandfonline","wiley","elsevier","mdpi.com","hindawi","frontiersin","semanticscholar.org","orcid.org"].some(d => url.includes(d))) return "research";
  // Path-aware: publication/paper pages on profile-domain sites are still research
  if (url.includes("researchgate.net/publication")) return "research";
  if (url.includes("researchgate.net/figure")) return "research";
  if (url.includes("scholar.google") && !url.includes("/citations?user")) return "research";
  if (url.includes("academia.edu") && url.split("academia.edu")[1]?.includes("/Papers/")) return "research";
  // Profiles: institutional bio pages, social/self-published platforms
  if (s.fetched_by === "crawl") return "profile";
  if ([".edu",".ac.in",".res.in",".gov.in",".gov","icar.org","iit.ac","scholar.google","researchgate","academia.edu","linkedin","orcid"].some(d => url.includes(d))) return "profile";
  // News: everything else (DDG/Google web results, press, interviews)
  return "news";
}

function SourcesPanel({ profile, openedLinks, onLinkOpen, onProfileUpdate, relayPending, onRelayConsumed }: {
  profile: PersonProfile;
  openedLinks: Set<string>;
  onLinkOpen: (url: string) => void;
  onProfileUpdate: (p: PersonProfile) => void;
  relayPending?: { url: string; text: string } | null;
  onRelayConsumed?: () => void;
}) {
  const [srcTab, setSrcTab] = useState<SourceCategory | "all">("all");
  const [urlInput, setUrlInput] = useState("");
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [blockedUrl, setBlockedUrl] = useState<string | null>(null);

  const [pasteUrl, setPasteUrl] = useState("");
  const [pasteText, setPasteText] = useState("");
  const [pasteLoading, setPasteLoading] = useState(false);
  const [pasteError, setPasteError] = useState<string | null>(null);

  const [crawlSeeds, setCrawlSeeds] = useState("");
  const [crawlKeywords, setCrawlKeywords] = useState("");
  const [crawlLoading, setCrawlLoading] = useState(false);
  const [crawlResult, setCrawlResult] = useState<string | null>(null);
  const [crawlError, setCrawlError] = useState<string | null>(null);

  const [expandPaste, setExpandPaste] = useState(false);
  const [expandCrawl, setExpandCrawl] = useState(false);
  const [expandManual, setExpandManual] = useState(false);
  const [sentToBrowser, setSentToBrowser] = useState(false);
  const [browserFetchLoading, setBrowserFetchLoading] = useState(false);

  const [suggestions, setSuggestions] = useState<UrlSuggestion[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const [skipped, setSkipped] = useState<Set<string>>(new Set());

  async function loadSuggestions() {
    setSuggestionsLoading(true); setSuggestionsError(null);
    try {
      const results = await suggestUrls(profile.name);
      setSuggestions(results);
      setSkipped(new Set());
    } catch (e) { setSuggestionsError(String(e)); }
    finally { setSuggestionsLoading(false); }
  }

  useEffect(() => { loadSuggestions(); }, [profile.name]);

  async function handleApproveSuggestion(url: string) {
    setUrlInput(url);
    setSkipped(s => new Set([...s, url])); // hide from queue immediately
    setUrlLoading(true); setUrlError(null); setBlockedUrl(null); setPipelineMsg(null);
    try {
      const resp = await addSource(profile.name, url);
      const newSources = resp.source ? [...profile.sources, resp.source] : profile.sources;
      onProfileUpdate({
        ...profile,
        sources: newSources,
        claims: [...profile.claims, ...resp.new_claims],
        notability: resp.notability,
        ...(resp.researcher_ids !== undefined && { researcher_ids: resp.researcher_ids }),
        ...(resp.confirmed_ids !== undefined && { confirmed_ids: resp.confirmed_ids }),
      });
      if (resp.sent_to_browser) { setSentToBrowser(true); setBlockedUrl(url); }
      else if (resp.blocked && !resp.pipeline) { setBlockedUrl(url); setPasteUrl(url); setExpandPaste(true); }
      if (resp.pipeline) {
        const p = resp.pipeline;
        const parts: string[] = [];
        if (p.doi) parts.push(`DOI resolved: ${p.doi}`);
        if (p.openalex_author_id) parts.push(`OpenAlex author confirmed`);
        if ((p.openalex_works_added ?? 0) > 0) parts.push(`${p.openalex_works_added} papers added`);
        if (p.scopus_id) parts.push(`Scopus ID: ${p.scopus_id}`);
        if (parts.length) setPipelineMsg(parts.join(" · "));
      }
      setUrlInput("");
    } catch (e) { setUrlError(String(e)); }
    finally { setUrlLoading(false); }
  }

  async function handleFetchFromBrowser() {
    setBrowserFetchLoading(true);
    try {
      const resp = await fetchFromBrowser(profile.name);
      const newSources = resp.source ? [...profile.sources, resp.source] : profile.sources;
      onProfileUpdate({
        ...profile,
        sources: newSources,
        claims: [...profile.claims, ...resp.new_claims],
        notability: resp.notability,
        ...(resp.researcher_ids !== undefined && { researcher_ids: resp.researcher_ids }),
        ...(resp.confirmed_ids !== undefined && { confirmed_ids: resp.confirmed_ids }),
      });
      setSentToBrowser(false);
    } catch (e) { setUrlError(String(e)); }
    finally { setBrowserFetchLoading(false); }
  }

  // Wiki+ relay from browser_server: auto-populate paste panel with captured content
  useEffect(() => {
    if (!relayPending) return;
    setPasteUrl(relayPending.url);
    setPasteText(relayPending.text);
    setExpandPaste(true);
    onRelayConsumed?.();
  }, [relayPending]);
  const [idsLoading, setIdsLoading] = useState(false);
  const [idsError, setIdsError] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const [pipelineMsg, setPipelineMsg] = useState<string | null>(null);

  const isDuplicate = urlInput.trim() !== "" && profile.sources.some(s => s.url === urlInput.trim());

  async function handleAddUrl() {
    if (!urlInput.trim() || isDuplicate) return;
    setUrlLoading(true); setUrlError(null); setBlockedUrl(null); setPipelineMsg(null);
    try {
      const resp = await addSource(profile.name, urlInput.trim());
      const newSources = resp.source ? [...profile.sources, resp.source] : profile.sources;
      onProfileUpdate({
        ...profile,
        sources: newSources,
        claims: [...profile.claims, ...resp.new_claims],
        notability: resp.notability,
        ...(resp.researcher_ids !== undefined && { researcher_ids: resp.researcher_ids }),
        ...(resp.confirmed_ids !== undefined && { confirmed_ids: resp.confirmed_ids }),
      });
      if (resp.sent_to_browser) { setSentToBrowser(true); setBlockedUrl(urlInput.trim()); }
      else if (resp.blocked && !resp.pipeline) { setBlockedUrl(urlInput.trim()); setPasteUrl(urlInput.trim()); setExpandPaste(true); }
      if (resp.pipeline) {
        const p = resp.pipeline;
        const parts: string[] = [];
        if (p.doi) parts.push(`DOI resolved: ${p.doi}`);
        if (p.openalex_author_id) parts.push(`OpenAlex author confirmed`);
        if ((p.openalex_works_added ?? 0) > 0) parts.push(`${p.openalex_works_added} papers added`);
        if (p.scopus_id) parts.push(`Scopus ID: ${p.scopus_id}`);
        if (parts.length) setPipelineMsg(parts.join(" · "));
      }
      setUrlInput("");
    } catch (e) { setUrlError(String(e)); }
    finally { setUrlLoading(false); }
  }

  async function handleAddPaste() {
    if (!pasteUrl.trim() || !pasteText.trim()) return;
    setPasteLoading(true); setPasteError(null);
    try {
      const resp = await addSourcePaste(profile.name, pasteUrl.trim(), pasteText.trim());
      onProfileUpdate({ ...profile, sources: [...profile.sources, resp.source], claims: [...profile.claims, ...resp.new_claims], notability: resp.notability });
      setPasteUrl(""); setPasteText(""); setBlockedUrl(null); setExpandPaste(false);
    } catch (e) { setPasteError(String(e)); }
    finally { setPasteLoading(false); }
  }

  async function handleCrawl() {
    const seeds = crawlSeeds.split("\n").map(s => s.trim()).filter(Boolean);
    if (!seeds.length) return;
    const keywords = crawlKeywords.split(",").map(k => k.trim()).filter(Boolean);
    setCrawlLoading(true); setCrawlError(null); setCrawlResult(null);
    try {
      const resp = await deepCrawl(profile.name, seeds, keywords);
      const updated = await getSession(profile.name);
      onProfileUpdate(updated);
      setCrawlResult(`Crawled ${resp.nodes_crawled} pages · ${resp.relevant_sources} relevant sources · ${resp.new_claims} new claims`);
      setCrawlSeeds(""); setCrawlKeywords("");
    } catch (e) { setCrawlError(String(e)); }
    finally { setCrawlLoading(false); }
  }

  async function handleFindIds() {
    setIdsLoading(true); setIdsError(null);
    try {
      const resp = await findResearcherIds(profile.name);
      onProfileUpdate({ ...profile, researcher_ids: resp.researcher_ids, confirmed_ids: resp.confirmed_ids });
    } catch (e) { setIdsError(String(e)); }
    finally { setIdsLoading(false); }
  }

  async function handleRefreshPapers(idType: string, idValue: string, confirm?: boolean) {
    setRefreshingId(idType); setIdsError(null);
    try {
      const resp = await refreshPapers(profile.name, idType, idValue, confirm);
      onProfileUpdate({
        ...profile,
        sources: resp.sources as PersonProfile["sources"],
        claims: resp.claims as PersonProfile["claims"],
        notability: resp.notability,
        researcher_ids: resp.researcher_ids,
        confirmed_ids: resp.confirmed_ids,
      });
    } catch (e) { setIdsError(String(e)); }
    finally { setRefreshingId(null); }
  }

  const visibleSuggestions = suggestions.filter(s => !skipped.has(s.url) && !profile.sources.some(src => src.url === s.url));

  return (
    <div>
      {/* Suggestion queue — primary workflow */}
      <div className="card" style={{ borderTopLeftRadius: 0, borderTopRightRadius: 0, marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>Suggested sources</p>
          <div style={{ display: "flex", gap: 6 }}>
            <button onClick={handleFetchFromBrowser} disabled={browserFetchLoading} title="Load whatever page is currently open in the remote browser (port 7070) and add it as a source" style={{ fontSize: 12, background: "none", border: "1px solid #93c5fd", borderRadius: 6, padding: "3px 10px", cursor: "pointer", color: "#1d4ed8" }}>
              {browserFetchLoading ? "Importing…" : "Import current page"}
            </button>
            <button onClick={loadSuggestions} disabled={suggestionsLoading} style={{ fontSize: 12, background: "none", border: "1px solid var(--border)", borderRadius: 6, padding: "3px 10px", cursor: "pointer", color: "var(--muted)" }}>
              {suggestionsLoading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </div>

        {suggestionsLoading && (
          <div style={{ padding: "20px 0", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
            Searching for sources…
          </div>
        )}
        {suggestionsError && <p style={{ color: "var(--danger)", fontSize: 12, marginBottom: 8 }}>{suggestionsError}</p>}

        {!suggestionsLoading && visibleSuggestions.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8 }}>
            No new suggestions — add URLs manually below or refresh.
          </p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {visibleSuggestions.map(s => {
            const slotPriority: Record<string, "critical" | "high" | "low"> = {
              birth_date: "critical", known_for: "critical", award: "critical",
              affiliation: "high", position: "high", education: "high",
            };
            const fetchIcon = s.fetchable === "open" ? "Open" : s.fetchable === "needs_browser" ? "Needs browser" : "Paywalled";
            const fetchColor = s.fetchable === "open" ? "#16a34a" : s.fetchable === "needs_browser" ? "#d97706" : "#dc2626";
            const relColor = s.relevance === "high" ? "#16a34a" : s.relevance === "medium" ? "#d97706" : "#6b7280";

            async function viewInBrowser() {
              try {
                await fetch("http://localhost:7070/navigate", {
                  method: "POST", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ url: s.url }),
                });
                window.open("http://localhost:7070", "_blank");
              } catch { window.open(s.url, "_blank"); }
            }

            return (
              <div key={s.url} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "10px 12px", background: "var(--surface-dim, var(--bg))" }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <a href={s.url} target="_blank" rel="noreferrer" style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", textDecoration: "none", display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {s.title || s.url}
                    </a>
                    <p style={{ fontSize: 11, color: "var(--accent)", margin: "3px 0 2px", fontWeight: 500 }}>{s.reason}</p>
                    {s.query && (
                      <p style={{ fontSize: 10, color: "var(--muted)", margin: "0 0 4px", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        searched: {s.query}
                      </p>
                    )}

                    {/* Badges row */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 5 }}>
                      <span style={{ fontSize: 10, borderRadius: 4, padding: "1px 6px", fontWeight: 600, background: `${fetchColor}18`, color: fetchColor, border: `1px solid ${fetchColor}40` }}>
                        {fetchIcon}
                      </span>
                      <span style={{ fontSize: 10, borderRadius: 4, padding: "1px 6px", fontWeight: 600, background: `${relColor}18`, color: relColor, border: `1px solid ${relColor}40` }}>
                        {s.relevance} match
                      </span>
                      {s.completion_value > 0 && (
                        <span style={{ fontSize: 10, borderRadius: 4, padding: "1px 6px", fontWeight: 600, background: "rgba(99,102,241,0.1)", color: "var(--accent)", border: "1px solid rgba(99,102,241,0.3)" }}>
                          +{s.completion_value} pts
                        </span>
                      )}
                      {s.expected_slots.map(slot => {
                        const pri = slotPriority[slot];
                        const c = pri === "critical" ? "#dc2626" : pri === "high" ? "#d97706" : "#6b7280";
                        return (
                          <span key={slot} style={{ fontSize: 10, borderRadius: 4, padding: "1px 6px", background: `${c}15`, color: c, border: `1px solid ${c}30` }}>
                            {slot.replace(/_/g, " ")}
                          </span>
                        );
                      })}
                    </div>

                    <a href={s.url} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: "var(--muted)", display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {s.url}
                    </a>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4, flexShrink: 0 }}>
                    <button className="btn-primary" onClick={() => handleApproveSuggestion(s.url)} disabled={urlLoading} style={{ fontSize: 12, padding: "4px 12px" }}>
                      Add
                    </button>
                    <button onClick={viewInBrowser} style={{ fontSize: 12, padding: "4px 12px", background: "none", border: "1px solid #93c5fd", borderRadius: 6, cursor: "pointer", color: "#1d4ed8" }}>
                      View
                    </button>
                    <button onClick={() => setSkipped(sk => new Set([...sk, s.url]))} style={{ fontSize: 12, padding: "4px 12px", background: "none", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", color: "var(--muted)" }}>
                      Skip
                    </button>
                  </div>
                </div>
                {s.snippet && <p style={{ fontSize: 11, color: "var(--muted)", margin: "6px 0 0", lineHeight: 1.4, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{s.snippet}</p>}
              </div>
            );
          })}
        </div>

        {urlError && <p style={{ color: "var(--danger)", fontSize: 12, marginTop: 8 }}>{urlError}</p>}
        {pipelineMsg && <p style={{ fontSize: 12, color: "var(--success)", marginTop: 8, fontWeight: 600 }}>{pipelineMsg}</p>}
        {sentToBrowser && (
          <div style={{ marginTop: 8, padding: "10px 14px", background: "#eff6ff", border: "1px solid #93c5fd", borderRadius: 8, display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 13, color: "#1d4ed8", flex: 1 }}>Opened in remote browser — solve any CAPTCHA, then tap below.</span>
            <button className="btn-primary" onClick={handleFetchFromBrowser} disabled={browserFetchLoading} style={{ fontSize: 12, padding: "5px 14px", whiteSpace: "nowrap" }}>
              {browserFetchLoading ? "Fetching…" : "Fetch from browser"}
            </button>
          </div>
        )}
        {blockedUrl && !sentToBrowser && <p style={{ fontSize: 12, color: "var(--warning)", marginTop: 6 }}>Site blocked — paste content below.</p>}

        {/* Manual entry — secondary */}
        <div style={{ marginTop: 12 }}>
          <Expander label="Add URL manually" open={expandManual} onToggle={() => setExpandManual(v => !v)}>
            <div style={{ marginTop: 10 }}>
              <div style={{ display: "flex", gap: 8 }}>
                <input value={urlInput} onChange={e => setUrlInput(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddUrl()} placeholder="https://…" style={{ flex: 1, borderColor: isDuplicate ? "var(--warning)" : undefined }} />
                <button className="btn-primary" onClick={handleAddUrl} disabled={urlLoading || !urlInput.trim() || isDuplicate}>{urlLoading ? "Fetching…" : "Add"}</button>
              </div>
              {isDuplicate && <p style={{ color: "var(--warning)", fontSize: 12, marginTop: 6 }}>Already in your sources list.</p>}
            </div>
          </Expander>
        </div>

        <div style={{ marginTop: 8 }}>
          <Expander label="Paste text from blocked page / PDF" open={expandPaste} onToggle={() => setExpandPaste(v => !v)}>
            <div style={{ marginTop: 10 }}>
              <input value={pasteUrl} onChange={e => setPasteUrl(e.target.value)} placeholder="Source URL (for citation)" style={{ marginBottom: 8 }} />
              <textarea value={pasteText} onChange={e => setPasteText(e.target.value)} placeholder="Paste the page text here…" style={{ height: 110, resize: "vertical", fontFamily: "inherit" }} />
              {pasteError && <p style={{ color: "var(--danger)", fontSize: 12, marginTop: 4 }}>{pasteError}</p>}
              <button className="btn-primary" onClick={handleAddPaste} disabled={pasteLoading || !pasteUrl.trim() || !pasteText.trim()} style={{ marginTop: 8 }}>
                {pasteLoading ? "Submitting…" : "Submit pasted content"}
              </button>
            </div>
          </Expander>
        </div>

        <div style={{ marginTop: 8 }}>
          <Expander label="Deep crawl from seed URLs" open={expandCrawl} onToggle={() => setExpandCrawl(v => !v)}>
            <div style={{ marginTop: 10 }}>
              <textarea value={crawlSeeds} onChange={e => setCrawlSeeds(e.target.value)} placeholder={"Seed URLs, one per line"} style={{ height: 80, resize: "vertical", fontFamily: "inherit", marginBottom: 8 }} />
              <input value={crawlKeywords} onChange={e => setCrawlKeywords(e.target.value)} placeholder="Keywords (comma-separated, optional)" style={{ marginBottom: 8 }} />
              {crawlError && <p style={{ color: "var(--danger)", fontSize: 12, marginBottom: 6 }}>{crawlError}</p>}
              {crawlResult && <p style={{ color: "var(--success)", fontSize: 12, marginBottom: 6 }}>{crawlResult}</p>}
              <button className="btn-primary" onClick={handleCrawl} disabled={crawlLoading || !crawlSeeds.trim()}>
                {crawlLoading ? "Crawling…" : "Start crawl"}
              </button>
            </div>
          </Expander>
        </div>
      </div>

      {/* Relevance warning banner */}
      {(() => {
        const flagged = profile.sources.filter(s => s.relevance_flag === "likely_wrong");
        if (!flagged.length) return null;
        return (
          <div style={{ background: "#fff5f5", border: "1px solid #fca5a5", borderRadius: 8, padding: "10px 16px", marginBottom: 12, fontSize: 13 }}>
            <strong style={{ color: "var(--danger)" }}>
              {flagged.length} source{flagged.length > 1 ? "s" : ""} may be about a different person
            </strong>
            <span style={{ color: "var(--muted)", marginLeft: 8 }}>
              — review and reject them below to keep research clean.
            </span>
          </div>
        );
      })()}

      {/* Source sub-tabs */}
      {profile.sources.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--muted)", padding: "12px 0" }}>No sources yet.</p>
      ) : (() => {
        const counts = { research: 0, news: 0, profile: 0 };
        for (const s of profile.sources) counts[categorizeSource(s)]++;
        const visible = profile.sources
          .map((s, i) => ({ s, i }))
          .filter(({ s }) => srcTab === "all" || categorizeSource(s) === srcTab);

        return (
          <>
            <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)", marginBottom: 12 }}>
              {(["all", "research", "news", "profile"] as const).map(t => {
                const label = t === "all" ? `All (${profile.sources.length})`
                  : t === "research" ? `Research (${counts.research})`
                  : t === "news" ? `News (${counts.news})`
                  : `Profiles (${counts.profile})`;
                return (
                  <button key={t} onClick={() => setSrcTab(t)} style={{
                    padding: "8px 14px", fontSize: 12, fontWeight: srcTab === t ? 700 : 500,
                    background: "none", border: "none", cursor: "pointer",
                    borderBottom: srcTab === t ? "2px solid var(--primary)" : "2px solid transparent",
                    color: srcTab === t ? "var(--primary)" : "var(--muted)",
                  }}>
                    {label}
                  </button>
                );
              })}
            </div>

            {/* Researcher IDs strip — only shown on Research sub-tab */}
            {srcTab === "research" && (
              <ResearcherIdsStrip
                researcherIds={profile.researcher_ids || {}}
                confirmedIds={profile.confirmed_ids || {}}
                loading={idsLoading}
                refreshingId={refreshingId}
                error={idsError}
                onFind={handleFindIds}
                onRefresh={handleRefreshPapers}
              />
            )}

            {visible.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--muted)", padding: "12px 0" }}>
                No {srcTab} sources yet. Add URLs above or use targeted search in the Wikipedia Profile tab.
              </p>
            ) : visible.map(({ s, i }) => (
              <SourceCard
                key={s.url + i}
                source={s}
                sourceNumber={i + 1}
                profileName={profile.name}
                linkOpened={openedLinks.has(s.url)}
                onLinkOpen={() => onLinkOpen(s.url)}
                onVerified={(verified, newClaims, missingSlots) => {
                  const sources = profile.sources.map(src => src.url === s.url ? { ...src, human_verified: verified } : src);
                  onProfileUpdate({
                    ...profile,
                    sources,
                    claims: newClaims ? [...profile.claims, ...newClaims] : profile.claims,
                    missing_slots: missingSlots ?? profile.missing_slots,
                  });
                  // New profile_links may have been extracted from this source — refresh queue
                  if (verified) loadSuggestions();
                }}
                onRejected={result => {
                  onProfileUpdate({
                    ...profile,
                    sources: result.sources as PersonProfile["sources"],
                    claims: result.claims as PersonProfile["claims"],
                    notability: result.notability,
                  });
                }}
              />
            ))}
          </>
        );
      })()}
    </div>
  );
}

function SourceCard({ source, sourceNumber, profileName, linkOpened, onLinkOpen, onVerified, onRejected }: {
  source: Source;
  sourceNumber: number;
  profileName: string;
  linkOpened: boolean;
  onLinkOpen: () => void;
  onVerified: (v: boolean, newClaims?: Claim[], missingSlots?: string[]) => void;
  onRejected: (result: { sources: Source[]; claims: Claim[]; notability: NotabilityResult }) => void;
}) {
  const [verifying, setVerifying] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const [claimsExtracted, setClaimsExtracted] = useState(0);

  const tagClass = SOURCE_TAG_CLASS;
  const tagLabel = SOURCE_TAG_LABEL;

  async function handleVerify() {
    setVerifying(true);
    try {
      const resp = await verifySource(profileName, source.url, !source.human_verified);
      if (resp.new_claims?.length) setClaimsExtracted(resp.new_claims.length);
      onVerified(!source.human_verified, resp.new_claims ?? [], resp.missing_slots ?? []);
    } catch { /* silently ignore */ }
    finally { setVerifying(false); }
  }

  async function handleReject() {
    setRejecting(true);
    try {
      const result = await rejectSource(profileName, source.url, rejectReason);
      onRejected(result);
    } catch { setRejecting(false); setShowReject(false); }
  }

  return (
    <div className="card" style={{ marginBottom: 12, padding: "14px 18px" }}>
      {/* Top row: tag + publisher + open link */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 4, padding: "1px 8px", minWidth: 28, textAlign: "center" as const }}>
              #{sourceNumber}
            </span>
            <span className={`tag ${tagClass[source.reliability]}`}>{tagLabel[source.reliability]}</span>
            <FetchedByTag fetchedBy={source.fetched_by} userProvided={source.user_provided} />
            <RelevanceBadge flag={source.relevance_flag} />
            {source.human_verified && (
              <span style={{ fontSize: 11, color: "var(--success)", fontWeight: 700 }}>✓ Verified</span>
            )}
            {linkOpened && !source.human_verified && (
              <span style={{ fontSize: 11, color: "var(--muted)" }}>Link opened</span>
            )}
          </div>

          <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }} title={source.title}>
            {source.publisher || new URL(source.url).hostname.replace("www.", "")}
          </p>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 6 }} title={source.title}>
            {source.title.slice(0, 90)}{source.title.length > 90 ? "…" : ""}
          </p>
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer"
            onClick={onLinkOpen}
            style={{ fontSize: 11, color: "var(--primary)", display: "inline-block", wordBreak: "break-all" }}
          >
            {source.url.length > 70 ? source.url.slice(0, 70) + "…" : source.url} ↗
          </a>
        </div>
      </div>

      {/* Author match — the key trust signal for academic sources */}
      {source.author_match_status && source.author_match_status !== "no_data" && (
        <AuthorMatchBadge source={source} />
      )}

      {/* Snippet */}
      {source.snippet && (
        <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 8, lineHeight: 1.5, borderLeft: "2px solid var(--border)", paddingLeft: 10 }}>
          {source.snippet.slice(0, 200)}{source.snippet.length > 200 ? "…" : ""}
        </p>
      )}

      {/* Action row */}
      {!showReject && (
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button
            onClick={handleVerify}
            disabled={verifying}
            style={{
              padding: "6px 14px", fontSize: 12, fontWeight: 600, borderRadius: 6,
              border: `1px solid ${source.human_verified ? "var(--success)" : "var(--border)"}`,
              background: source.human_verified ? "#dcfce7" : "transparent",
              color: source.human_verified ? "var(--success)" : "var(--text)",
              cursor: "pointer",
            }}
          >
            {verifying ? "Extracting claims…" : source.human_verified ? `✓ Verified${claimsExtracted ? ` · ${claimsExtracted} claims` : ""}` : "Confirm & extract claims"}
          </button>
          <button
            onClick={() => setShowReject(true)}
            style={{ padding: "6px 14px", fontSize: 12, fontWeight: 600, borderRadius: 6, border: "1px solid var(--border)", background: "transparent", color: "var(--danger)", cursor: "pointer" }}
          >
            Reject
          </button>
        </div>
      )}

      {/* Reject confirmation */}
      {showReject && (
        <div style={{ marginTop: 12, padding: "12px", background: "#fff5f5", border: "1px solid #fca5a5", borderRadius: 8 }}>
          <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: "var(--danger)" }}>
            Reject this source?
          </p>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>
            All claims extracted from this source will be removed.
          </p>
          <input
            value={rejectReason}
            onChange={e => setRejectReason(e.target.value)}
            placeholder="Reason (optional — e.g. wrong person, unreliable content)"
            style={{ marginBottom: 10, fontSize: 13 }}
            autoFocus
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={handleReject}
              disabled={rejecting}
              style={{ padding: "7px 16px", fontSize: 12, fontWeight: 700, borderRadius: 6, border: "none", background: "var(--danger)", color: "#fff", cursor: "pointer" }}
            >
              {rejecting ? "Removing…" : "Confirm rejection"}
            </button>
            <button
              onClick={() => { setShowReject(false); setRejectReason(""); }}
              style={{ padding: "7px 16px", fontSize: 12, fontWeight: 600, borderRadius: 6, border: "1px solid var(--border)", background: "transparent", cursor: "pointer" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Timeline tab ─────────────────────────────────────────────────────────────

const TIMELINE_FIELDS = ["birth_date", "education", "affiliation", "position", "award", "death_date"];

const FIELD_COLOR: Record<string, string> = {
  birth_date:  "#6366f1",
  death_date:  "#6b7280",
  education:   "#8b5cf6",
  affiliation: "#0891b2",
  position:    "#0d9488",
  award:       "#d97706",
  known_for:   "#16a34a",
};

const FIELD_LABEL: Record<string, string> = {
  birth_date:  "Birth",
  death_date:  "Death",
  education:   "Education",
  affiliation: "Affiliation",
  position:    "Position",
  award:       "Award",
  known_for:   "Known for",
};

function parseFirstYear(s: string | null | undefined): number | null {
  if (!s) return null;
  const m = s.match(/\b(1[89]\d\d|20\d\d)\b/);
  return m ? parseInt(m[1]) : null;
}

function TimelineTab({ profile }: { profile: PersonProfile }) {
  // Build event list from temporal claims
  interface TLEvent {
    year: number | null;
    period: string;
    text: string;
    field: string;
    source: Source | null;
    source_url: string | null;
  }

  const events: TLEvent[] = [];

  // Birth from profile-level field (may not have a claim)
  if (profile.birth_date && !profile.claims.some(c => c.field === "birth_date")) {
    events.push({
      year: parseFirstYear(profile.birth_date),
      period: profile.birth_date,
      text: `Born ${profile.birth_date}`,
      field: "birth_date",
      source: null,
      source_url: null,
    });
  }

  for (const claim of profile.claims) {
    if (!TIMELINE_FIELDS.includes(claim.field)) continue;
    const src = claim.source_url ? profile.sources.find(s => s.url === claim.source_url) ?? null : null;
    const year = parseFirstYear(claim.date_context) ?? parseFirstYear(claim.text);
    events.push({
      year,
      period: claim.date_context || "",
      text: claim.text,
      field: claim.field,
      source: src,
      source_url: claim.source_url ?? null,
    });
  }

  const dated   = events.filter(e => e.year !== null).sort((a, b) => a.year! - b.year!);
  const undated = events.filter(e => e.year === null);

  if (events.length === 0) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
        No timeline events yet. Confirm sources to extract claims with dates.
      </div>
    );
  }

  function EventRow({ ev }: { ev: TLEvent }) {
    const color = FIELD_COLOR[ev.field] ?? "#6b7280";
    const dotStyle: string = ev.source?.reliability === "reliable_secondary"
      ? "solid"
      : ev.source ? "primary" : "empty";
    return (
      <div style={{ display: "flex", gap: 0, marginBottom: 10, position: "relative" }}>
        {/* Year column */}
        <div style={{ width: 52, flexShrink: 0, paddingTop: 2 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: ev.year ? color : "var(--muted)" }}>
            {ev.period || "—"}
          </span>
        </div>
        {/* Dot + line */}
        <div style={{ width: 20, flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{
            width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
            marginTop: 3,
            background: dotStyle === "solid" ? color : dotStyle === "primary" ? "white" : "var(--bg)",
            border: `2px solid ${dotStyle === "empty" ? "var(--muted)" : color}`,
            boxShadow: dotStyle === "solid" ? `0 0 0 2px ${color}30` : "none",
          }} />
          <div style={{ flex: 1, width: 2, background: "var(--border)", minHeight: 8 }} />
        </div>
        {/* Content */}
        <div style={{ flex: 1, paddingLeft: 8, paddingBottom: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
            <span style={{ fontSize: 10, fontWeight: 700, color, background: `${color}15`, borderRadius: 4, padding: "1px 5px" }}>
              {FIELD_LABEL[ev.field] ?? ev.field}
            </span>
            {!ev.source && ev.source_url === null && (
              <span style={{ fontSize: 10, color: "var(--warning)", fontWeight: 600 }}>no source</span>
            )}
          </div>
          <p style={{ fontSize: 13, margin: 0, lineHeight: 1.4 }}>{ev.text}</p>
          {ev.source && (
            <a href={ev.source_url!} target="_blank" rel="noreferrer"
              style={{ fontSize: 11, color: "var(--primary)", marginTop: 2, display: "inline-block" }}>
              {ev.source.publisher || new URL(ev.source_url!).hostname.replace("www.", "")} ↗
            </a>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ paddingTop: 20 }}>
      <div style={{ position: "relative" }}>
        {dated.map((ev, i) => <EventRow key={i} ev={ev} />)}
        {undated.length > 0 && (
          <>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, color: "var(--muted)", margin: "16px 0 10px 72px" }}>
              Undated
            </p>
            {undated.map((ev, i) => <EventRow key={`u${i}`} ev={ev} />)}
          </>
        )}
      </div>

      <div style={{ marginTop: 16, padding: "10px 12px", background: "var(--bg)", borderRadius: 8, fontSize: 11, color: "var(--muted)" }}>
        <strong>Legend:</strong>&nbsp;
        <span style={{ marginRight: 10 }}>Filled dot = reliable secondary source</span>
        <span style={{ marginRight: 10 }}>Outlined dot = primary/self-published</span>
        <span>Empty dot = no source yet</span>
      </div>
    </div>
  );
}

// ── Profile tab — Wikipedia slot view ────────────────────────────────────────

const SLOT_LABELS: Record<string, string> = {
  full_name: "Full name",
  birth_date: "Date of birth",
  birth_place: "Place of birth",
  nationality: "Nationality",
  affiliation: "Institution",
  position: "Position / title",
  field: "Research field",
  education: "Education",
  known_for: "Known for",
  award: "Awards",
};

const SLOT_HINTS: Record<string, string> = {
  birth_date:   "news article, obituary, or institutional bio",
  birth_place:  "news article or institutional bio",
  nationality:  "institutional bio or news",
  affiliation:  "institution website (faculty/staff page)",
  position:     "institution website (faculty/staff page)",
  field:        "institution website or research profile",
  education:    "institution website or CV/bio page",
  known_for:    "news article or research profile",
  award:        "press release, news, or institution website",
  full_name:    "institution website or official document",
};

const SLOT_SECTIONS: { label: string; slots: string[] }[] = [
  { label: "Infobox", slots: ["full_name", "birth_date", "birth_place", "nationality"] },
  { label: "Career", slots: ["affiliation", "position", "field", "education"] },
  { label: "Recognition", slots: ["known_for", "award"] },
];

type FillMode = "search" | "url" | "manual";

function ProfileTab({ profile, onProfileUpdate }: {
  profile: PersonProfile;
  onProfileUpdate: (p: PersonProfile) => void;
}) {
  const [activeMode, setActiveMode] = useState<Record<string, FillMode | null>>({});
  const [busySlot, setBusySlot] = useState<string | null>(null);
  const [slotError, setSlotError] = useState<Record<string, string>>({});
  const [hintInputs, setHintInputs] = useState<Record<string, string>>({});
  const [urlInputs, setUrlInputs] = useState<Record<string, string>>({});
  const [manualInputs, setManualInputs] = useState<Record<string, string>>({});

  function setMode(slot: string, mode: FillMode | null) {
    setActiveMode(m => ({ ...m, [slot]: mode }));
    setSlotError(e => ({ ...e, [slot]: "" }));
  }

  // Build slot → best claim map (prefer confirmed/edited)
  const slotClaims: Record<string, typeof profile.claims[0]> = {};
  for (const claim of profile.claims) {
    const existing = slotClaims[claim.field];
    if (!existing || claim.verification === "confirmed" || claim.verification === "edited") {
      slotClaims[claim.field] = claim;
    }
  }

  // Profile-level user-typed values (unsourced fills)
  const profileFills: Record<string, string> = {};
  if (profile.birth_date)  profileFills.birth_date  = profile.birth_date;
  if (profile.birth_place) profileFills.birth_place = profile.birth_place;
  if (profile.nationality) profileFills.nationality = profile.nationality;
  if (profile.affiliation) profileFills.affiliation = profile.affiliation;
  if (profile.field)       profileFills.field        = profile.field;
  if (profile.full_name)   profileFills.full_name    = profile.full_name;

  async function handleSearch(slot: string) {
    setBusySlot(slot);
    setSlotError(e => ({ ...e, [slot]: "" }));
    try {
      const hint = hintInputs[slot]?.trim() || undefined;
      const resp = await targetedSearch(profile.name, slot, hint);
      onProfileUpdate({
        ...profile,
        sources: [...profile.sources, ...resp.sources],
        claims: [...profile.claims, ...resp.new_claims],
        missing_slots: resp.missing_slots,
        notability: resp.notability,
      });
      setMode(slot, null);
    } catch (e) {
      setSlotError(err => ({ ...err, [slot]: String(e) }));
    } finally {
      setBusySlot(null);
    }
  }

  async function handleAddUrl(slot: string) {
    const url = urlInputs[slot]?.trim();
    if (!url) return;
    setBusySlot(slot);
    setSlotError(e => ({ ...e, [slot]: "" }));
    try {
      const resp = await addSource(profile.name, url);
      const newSources = resp.source ? [...profile.sources, resp.source] : profile.sources;
      onProfileUpdate({
        ...profile,
        sources: newSources,
        claims: [...profile.claims, ...resp.new_claims],
        notability: resp.notability,
      });
      setUrlInputs(u => ({ ...u, [slot]: "" }));
      setMode(slot, null);
    } catch (e) {
      setSlotError(err => ({ ...err, [slot]: String(e) }));
    } finally {
      setBusySlot(null);
    }
  }

  async function handleManual(slot: string) {
    const text = manualInputs[slot]?.trim();
    if (!text) return;
    setBusySlot(slot);
    setSlotError(e => ({ ...e, [slot]: "" }));
    try {
      const resp = await addDocumentFact(profile.name, slot, text);
      onProfileUpdate({ ...profile, claims: [...profile.claims, resp.claim] });
      setManualInputs(m => ({ ...m, [slot]: "" }));
      setMode(slot, null);
    } catch (e) {
      setSlotError(err => ({ ...err, [slot]: String(e) }));
    } finally {
      setBusySlot(null);
    }
  }

  const missingSet = new Set(profile.missing_slots ?? []);

  return (
    <div style={{ paddingTop: 16 }}>
      {SLOT_SECTIONS.map(section => (
        <div key={section.label} style={{ marginBottom: 28 }}>
          <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, color: "var(--muted)", marginBottom: 10 }}>
            {section.label}
          </p>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {section.slots.map(slot => {
              const claim = slotClaims[slot];
              const profileVal = profileFills[slot];
              const isMissing = missingSet.has(slot);
              const src = claim?.source_url ? profile.sources.find(s => s.url === claim.source_url) : null;
              const mode = activeMode[slot] ?? null;
              const busy = busySlot === slot;
              const err = slotError[slot];

              return (
                <div key={slot} style={{
                  display: "grid", gridTemplateColumns: "130px 1fr",
                  gap: 14, padding: "12px 0", borderBottom: "1px solid var(--border)",
                }}>
                  {/* Label col */}
                  <div style={{ paddingTop: 1 }}>
                    <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", marginBottom: 3 }}>
                      {SLOT_LABELS[slot] ?? slot}
                    </p>
                    {claim && <span style={{ fontSize: 10, fontWeight: 700, color: "var(--success)" }}>Sourced</span>}
                    {!claim && profileVal && <span style={{ fontSize: 10, fontWeight: 700, color: "var(--warning)" }}>Unsourced</span>}
                    {isMissing && <span style={{ fontSize: 10, fontWeight: 700, color: "var(--danger)" }}>Missing</span>}
                  </div>

                  {/* Value col */}
                  <div>
                    {/* Filled value */}
                    {claim && (
                      <div style={{ marginBottom: isMissing ? 0 : 0 }}>
                        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 4 }}>
                          <p style={{ fontSize: 13, lineHeight: 1.5, margin: 0 }}>{claim.text}</p>
                          {claim.date_context && (
                            <span style={{ fontSize: 11, color: "var(--muted)", fontStyle: "italic", whiteSpace: "nowrap" }}>
                              {claim.date_context}
                            </span>
                          )}
                        </div>
                        {src && (
                          <a href={claim.source_url!} target="_blank" rel="noreferrer"
                            style={{ fontSize: 11, color: "var(--primary)", display: "inline-flex", alignItems: "center", gap: 5 }}>
                            <span className={`tag ${SOURCE_TAG_CLASS[src.reliability]}`} style={{ fontSize: 10, padding: "0 5px" }}>
                              {SOURCE_TAG_LABEL[src.reliability]}
                            </span>
                            <span>{src.publisher}</span>
                            <span>↗</span>
                          </a>
                        )}
                      </div>
                    )}

                    {/* Unsourced from form */}
                    {!claim && profileVal && (
                      <p style={{ fontSize: 13, color: "var(--muted)", fontStyle: "italic", marginBottom: 8 }}>
                        {profileVal}
                        <span style={{ fontSize: 11, marginLeft: 6 }}>(you entered this — find a source to cite it)</span>
                      </p>
                    )}

                    {/* Missing — show fill options */}
                    {isMissing && !claim && (
                      <div>
                        <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>
                          Best source: <strong>{SLOT_HINTS[slot]}</strong>
                        </p>

                        {/* Mode selector buttons */}
                        {mode === null && (
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            <button onClick={() => setMode(slot, "search")} style={modeBtn}>
                              Search news
                            </button>
                            <button onClick={() => setMode(slot, "url")} style={modeBtn}>
                              Paste URL
                            </button>
                            <button onClick={() => setMode(slot, "manual")} style={modeBtn}>
                              Enter manually
                            </button>
                          </div>
                        )}

                        {/* Search mode */}
                        {mode === "search" && (
                          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <input
                                value={hintInputs[slot] ?? ""}
                                onChange={e => setHintInputs(h => ({ ...h, [slot]: e.target.value }))}
                                onKeyDown={e => e.key === "Enter" && handleSearch(slot)}
                                placeholder="Hint to narrow search (optional)"
                                style={{ fontSize: 12, padding: "5px 10px", flex: "1 1 180px" }}
                                autoFocus
                              />
                              <button className="btn-primary" onClick={() => handleSearch(slot)} disabled={busy}
                                style={{ fontSize: 12, padding: "5px 14px" }}>
                                {busy ? "Searching…" : "Search news"}
                              </button>
                              <button onClick={() => setMode(slot, null)} style={{ ...modeBtn, border: "none" }}>Cancel</button>
                            </div>
                            {err && <p style={{ fontSize: 12, color: "var(--danger)" }}>{err}</p>}
                          </div>
                        )}

                        {/* URL mode */}
                        {mode === "url" && (
                          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <input
                                value={urlInputs[slot] ?? ""}
                                onChange={e => setUrlInputs(u => ({ ...u, [slot]: e.target.value }))}
                                onKeyDown={e => e.key === "Enter" && handleAddUrl(slot)}
                                placeholder="https://institution.edu/person…"
                                style={{ fontSize: 12, padding: "5px 10px", flex: "1 1 220px" }}
                                autoFocus
                              />
                              <button className="btn-primary" onClick={() => handleAddUrl(slot)}
                                disabled={busy || !urlInputs[slot]?.trim()}
                                style={{ fontSize: 12, padding: "5px 14px" }}>
                                {busy ? "Fetching…" : "Add source"}
                              </button>
                              <button onClick={() => setMode(slot, null)} style={{ ...modeBtn, border: "none" }}>Cancel</button>
                            </div>
                            {err && <p style={{ fontSize: 12, color: "var(--danger)" }}>{err}</p>}
                          </div>
                        )}

                        {/* Manual entry mode */}
                        {mode === "manual" && (
                          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <input
                                value={manualInputs[slot] ?? ""}
                                onChange={e => setManualInputs(m => ({ ...m, [slot]: e.target.value }))}
                                onKeyDown={e => e.key === "Enter" && handleManual(slot)}
                                placeholder={`Enter ${SLOT_LABELS[slot]?.toLowerCase() ?? slot}…`}
                                style={{ fontSize: 12, padding: "5px 10px", flex: "1 1 220px" }}
                                autoFocus
                              />
                              <button className="btn-primary" onClick={() => handleManual(slot)}
                                disabled={busy || !manualInputs[slot]?.trim()}
                                style={{ fontSize: 12, padding: "5px 14px" }}>
                                {busy ? "Saving…" : "Save (no citation)"}
                              </button>
                              <button onClick={() => setMode(slot, null)} style={{ ...modeBtn, border: "none" }}>Cancel</button>
                            </div>
                            <p style={{ fontSize: 11, color: "var(--warning)" }}>
                              {"Manual entries get {{citation needed}} in the draft — add a URL source to cite it properly."}
                            </p>
                            {err && <p style={{ fontSize: 12, color: "var(--danger)" }}>{err}</p>}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Publications — list section, not a single slot */}
      <div style={{ marginBottom: 24 }}>
        <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, color: "var(--muted)", marginBottom: 10 }}>
          Publications ({profile.claims.filter(c => c.field === "publication").length})
        </p>
        {profile.claims.filter(c => c.field === "publication").length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--muted)" }}>No publications extracted yet. Add DOI or paper URLs in Sources.</p>
        ) : (
          profile.claims.filter(c => c.field === "publication").map((c, i) => {
            const src = c.source_url ? profile.sources.find(s => s.url === c.source_url) : null;
            return (
              <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", display: "flex", gap: 10 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", minWidth: 22, paddingTop: 2 }}>{i + 1}.</span>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 13, lineHeight: 1.5 }}>{c.text}</p>
                  {src && (
                    <a href={c.source_url!} target="_blank" rel="noreferrer"
                      style={{ fontSize: 11, color: "var(--primary)" }}>
                      {src.publisher} ↗
                    </a>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

const modeBtn: React.CSSProperties = {
  fontSize: 12, padding: "5px 12px", borderRadius: 6,
  border: "1px solid var(--border)", background: "var(--bg)",
  color: "var(--text)", cursor: "pointer", fontWeight: 600,
};

// ── Claims section (Review tab) ───────────────────────────────────────────────

function ClaimsSection({ claims, allClaims, profile, onProfileUpdate, emptyMessage }: {
  claims: Claim[];
  allClaims: Claim[];
  profile: PersonProfile;
  onProfileUpdate: (p: PersonProfile) => void;
  emptyMessage: string;
}) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [loading, setLoading] = useState<number | null>(null);

  if (claims.length === 0) {
    return <p style={{ fontSize: 13, color: "var(--muted)", padding: "20px 0" }}>{emptyMessage}</p>;
  }

  async function doVerify(globalIndex: number, action: "confirm" | "edit" | "skip", text?: string) {
    setLoading(globalIndex);
    try {
      const resp = await verifyClaim(profile.name, globalIndex, action, text);
      const updated = [...allClaims];
      updated[globalIndex] = resp.claim;
      onProfileUpdate({ ...profile, claims: updated });
    } catch { /* silently ignore */ }
    finally { setLoading(null); setEditingIndex(null); }
  }

  const claimIndexMap = new Map(allClaims.map((c, i) => [c, i]));

  const verificationColor: Record<string, string> = {
    unverified: "var(--muted)",
    confirmed: "var(--success)",
    edited: "var(--primary)",
    skipped: "var(--border)",
  };

  return (
    <div>
      {claims.map(claim => {
        const globalIndex = claimIndexMap.get(claim) ?? -1;
        const isEditing = editingIndex === globalIndex;
        const isLoading = loading === globalIndex;
        return (
          <div key={globalIndex} style={{
            padding: "14px 0", borderBottom: "1px solid var(--border)",
            opacity: claim.verification === "skipped" ? 0.45 : 1,
          }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", gap: 6, marginBottom: 5, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--muted)" }}>
                    {claim.field}
                  </span>
                  {claim.verification !== "unverified" && (
                    <span style={{ fontSize: 11, fontWeight: 700, color: verificationColor[claim.verification] }}>
                      · {claim.verification}
                    </span>
                  )}
                  {claim.user_provided && (
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>· manual entry</span>
                  )}
                </div>

                {isEditing ? (
                  <textarea
                    value={editText}
                    onChange={e => setEditText(e.target.value)}
                    style={{ height: 72, resize: "vertical", fontFamily: "inherit", fontSize: 13 }}
                    autoFocus
                  />
                ) : (
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                    <p style={{ fontSize: 13, lineHeight: 1.6, margin: 0 }}>{claim.text}</p>
                    {claim.date_context && (
                      <span style={{ fontSize: 11, color: "var(--muted)", fontStyle: "italic", whiteSpace: "nowrap" }}>
                        {claim.date_context}
                      </span>
                    )}
                  </div>
                )}

                <div style={{ marginTop: 5 }}>
                  {claim.source_url ? (() => {
                    const srcIdx = profile.sources.findIndex(s => s.url === claim.source_url);
                    const src = srcIdx >= 0 ? profile.sources[srcIdx] : null;
                    const title = src?.title ?? claim.source_url ?? "";
                    const shortTitle = title.length > 70 ? title.slice(0, 70) + "…" : title;
                    return (
                      <a href={claim.source_url} target="_blank" rel="noreferrer"
                        style={{ fontSize: 11, color: "var(--primary)", display: "inline-flex", alignItems: "center", gap: 5, flexWrap: "wrap" }}>
                        {srcIdx >= 0 && <strong style={{ fontWeight: 700 }}>[{srcIdx + 1}]</strong>}
                        <span>{shortTitle}</span>
                        {src && <span className={`tag ${SOURCE_TAG_CLASS[src.reliability]}`} style={{ fontSize: 10, padding: "0px 5px", lineHeight: "16px" }}>{SOURCE_TAG_LABEL[src.reliability]}</span>}
                        <span>↗</span>
                      </a>
                    );
                  })() : (
                    <span style={{ fontSize: 11, color: "var(--warning)" }}>
                      {"No source · will get {{citation needed}}"}
                    </span>
                  )}
                </div>
              </div>

              {/* Action buttons — only for unverified/skipped */}
              {(claim.verification === "unverified" || claim.verification === "skipped") && !isEditing && (
                <div style={{ display: "flex", flexDirection: "column", gap: 4, flexShrink: 0 }}>
                  <ActionBtn onClick={() => doVerify(globalIndex, "confirm")} disabled={isLoading} color="var(--success)" title="Confirm">✓</ActionBtn>
                  <ActionBtn onClick={() => { setEditingIndex(globalIndex); setEditText(claim.text); }} disabled={isLoading} color="var(--primary)" title="Edit">✎</ActionBtn>
                  <ActionBtn onClick={() => doVerify(globalIndex, "skip")} disabled={isLoading} color="var(--muted)" title="Skip">✗</ActionBtn>
                </div>
              )}
              {/* For confirmed/edited, just allow editing */}
              {(claim.verification === "confirmed" || claim.verification === "edited") && !isEditing && (
                <ActionBtn onClick={() => { setEditingIndex(globalIndex); setEditText(claim.text); }} disabled={isLoading} color="var(--primary)" title="Edit">✎</ActionBtn>
              )}
              {isEditing && (
                <div style={{ display: "flex", flexDirection: "column", gap: 4, flexShrink: 0 }}>
                  <ActionBtn onClick={() => doVerify(globalIndex, "edit", editText)} disabled={isLoading} color="var(--primary)" title="Save">✓</ActionBtn>
                  <ActionBtn onClick={() => setEditingIndex(null)} disabled={isLoading} color="var(--muted)" title="Cancel">✗</ActionBtn>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ActionBtn({ onClick, disabled, color, title, children }: {
  onClick: () => void; disabled: boolean; color: string; title: string; children: React.ReactNode;
}) {
  return (
    <button onClick={onClick} disabled={disabled} title={title} style={{
      width: 28, height: 28, padding: 0, borderRadius: 6, background: "var(--bg)",
      border: "1px solid var(--border)", color, fontSize: 14, fontWeight: 700,
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      {children}
    </button>
  );
}

// ── Researcher IDs strip ──────────────────────────────────────────────────────

const ID_META: Record<string, { label: string; url: (id: string) => string; color: string }> = {
  orcid:            { label: "ORCID",            url: id => `https://orcid.org/${id}`,                                  color: "#a6ce39" },
  google_scholar:   { label: "Google Scholar",   url: id => `https://scholar.google.com/citations?user=${id}`,          color: "#4285f4" },
  semantic_scholar: { label: "Semantic Scholar", url: id => `https://www.semanticscholar.org/author/${id}`,             color: "#1a73e8" },
  scopus:           { label: "Scopus",           url: id => `https://www.scopus.com/authid/detail.uri?authorId=${id}`,  color: "#f90" },
  researchgate:     { label: "ResearchGate",     url: id => `https://www.researchgate.net/profile/${id}`,               color: "#00ccbb" },
  openalex:         { label: "OpenAlex",         url: id => `https://openalex.org/authors/${id}`,                        color: "#6b7280" },
};

function ResearcherIdsStrip({
  researcherIds,
  confirmedIds,
  loading,
  refreshingId,
  error,
  onFind,
  onRefresh,
}: {
  researcherIds: Record<string, string>;
  confirmedIds: Record<string, boolean>;
  loading: boolean;
  refreshingId: string | null;
  error: string | null;
  onFind: () => void;
  onRefresh: (idType: string, idValue: string, confirm?: boolean) => void;
}) {
  const hasIds = Object.keys(researcherIds).length > 0;

  return (
    <div style={{ marginBottom: 14, padding: "10px 14px", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 8 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: hasIds ? 10 : 0 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
          Researcher Profiles
        </span>
        <button
          className="btn-ghost"
          onClick={onFind}
          disabled={loading}
          style={{ fontSize: 12, padding: "3px 10px" }}
        >
          {loading ? "Searching…" : hasIds ? "Re-scan" : "Find profiles"}
        </button>
      </div>

      {error && <p style={{ fontSize: 12, color: "var(--danger)", margin: "4px 0 0" }}>{error}</p>}

      {!hasIds && !loading && (
        <p style={{ fontSize: 12, color: "var(--muted)", margin: "4px 0 0" }}>
          Click "Find profiles" to search for ORCID, Google Scholar, and other researcher IDs.
        </p>
      )}

      {hasIds && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {Object.entries(researcherIds).map(([idType, idValue]) => {
            const meta = ID_META[idType];
            const confirmed = confirmedIds[idType] === true;
            const canRefresh = idType === "orcid" || idType === "semantic_scholar";
            return (
              <div key={idType} style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "white", border: "1px solid var(--border)", borderRadius: 6,
                padding: "5px 10px", fontSize: 12,
              }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: meta?.color ?? "#888", flexShrink: 0 }} />
                <a href={meta ? meta.url(idValue) : "#"} target="_blank" rel="noreferrer"
                  style={{ fontWeight: 600, color: "inherit", textDecoration: "none" }}>
                  {meta?.label ?? idType}
                </a>
                <span style={{ color: "var(--muted)", fontFamily: "monospace", fontSize: 11 }}>{idValue.slice(0, 18)}{idValue.length > 18 ? "…" : ""}</span>
                {confirmed ? (
                  <span style={{ fontSize: 10, background: "#dcfce7", color: "var(--success)", borderRadius: 4, padding: "1px 5px", fontWeight: 700 }}>Validated</span>
                ) : (
                  <span style={{ fontSize: 10, background: "#fef9c3", color: "#92400e", borderRadius: 4, padding: "1px 5px" }}>Unverified</span>
                )}
                {canRefresh && (
                  <button
                    className="btn-ghost"
                    onClick={() => onRefresh(idType, idValue, !confirmed)}
                    disabled={refreshingId === idType}
                    style={{ fontSize: 11, padding: "2px 7px" }}
                  >
                    {refreshingId === idType ? "Loading…" : confirmed ? "Refresh papers" : "Confirm & fetch"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Provenance tag ────────────────────────────────────────────────────────────

function RelevanceBadge({ flag }: { flag: Source["relevance_flag"] }) {
  if (flag === "unscored" || flag === "relevant") return null;
  if (flag === "likely_wrong") return (
    <span style={{ fontSize: 11, fontWeight: 700, background: "#fee2e2", color: "var(--danger)", borderRadius: 4, padding: "1px 7px" }}>
      Wrong person?
    </span>
  );
  // uncertain
  return (
    <span style={{ fontSize: 11, fontWeight: 600, background: "#fef9c3", color: "#92400e", borderRadius: 4, padding: "1px 7px" }}>
      Unconfirmed
    </span>
  );
}

function FetchedByTag({ fetchedBy, userProvided }: { fetchedBy: Source["fetched_by"]; userProvided: boolean }) {
  if (userProvided) return <span style={{ fontSize: 11, background: "#e0e7ff", color: "#3730a3", borderRadius: 4, padding: "1px 7px", fontWeight: 600 }}>Manual</span>;
  const labels: Record<string, string> = {
    semantic_scholar: "Semantic Scholar",
    google_search: "Google Search",
    duckduckgo: "DuckDuckGo",
    crawl: "Crawl",
    user: "Manual",
    openalex: "OpenAlex",
    orcid: "ORCID",
  };
  if (!fetchedBy || !labels[fetchedBy]) return null;
  return <span style={{ fontSize: 11, background: "#f1f5f9", color: "#64748b", borderRadius: 4, padding: "1px 7px" }}>{labels[fetchedBy]}</span>;
}

// ── Author match badge ────────────────────────────────────────────────────────

function AuthorMatchBadge({ source }: { source: Source }) {
  const { author_match_status: status, author_match_name: name, author_match_affiliation: affil, all_paper_authors: all } = source;
  const [showAll, setShowAll] = useState(false);

  const cfg: Record<string, { bg: string; border: string; color: string; icon: string; label: string }> = {
    confirmed: { bg: "#dcfce7", border: "#86efac", color: "var(--success)", icon: "✓", label: "Author confirmed" },
    possible:  { bg: "#eff6ff", border: "#bfdbfe", color: "var(--primary)", icon: "?", label: "Author name matches — affiliation unverified" },
    wrong_person: { bg: "#fee2e2", border: "#fca5a5", color: "var(--danger)", icon: "✗", label: "Different person with same name" },
    not_found: { bg: "#fff7ed", border: "#fed7aa", color: "var(--warning)", icon: "!", label: "Author not found in paper" },
  };

  const c = cfg[status ?? "not_found"] ?? cfg.not_found;

  return (
    <div style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 6, padding: "8px 12px", marginTop: 10 }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 6 }}>
        <span style={{ color: c.color, fontWeight: 700, fontSize: 13, flexShrink: 0 }}>{c.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: c.color }}>{c.label}</span>
          {name && (
            <span style={{ fontSize: 12, color: "var(--text)", marginLeft: 6 }}>
              — <strong>{name}</strong>{affil ? ` (${affil})` : ""}
            </span>
          )}
          {status === "not_found" && all.length > 0 && (
            <div style={{ marginTop: 4 }}>
              <button
                onClick={() => setShowAll(v => !v)}
                style={{ background: "none", border: "none", padding: 0, fontSize: 11, color: "var(--primary)", cursor: "pointer", fontWeight: 600 }}
              >
                {showAll ? "▾" : "▸"} {all.length} authors on this paper
              </button>
              {showAll && (
                <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
                  {all.join(", ")}
                </p>
              )}
            </div>
          )}
          {status === "wrong_person" && all.length > 0 && (
            <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
              Paper authors: {all.join(", ")}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Shared UI ─────────────────────────────────────────────────────────────────

function Expander({ label, open, onToggle, children }: {
  label: string; open: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <div>
      <button onClick={onToggle} style={{ background: "none", border: "none", padding: 0, fontSize: 12, color: "var(--primary)", fontWeight: 600, cursor: "pointer" }}>
        {open ? "▾" : "▸"} {label}
      </button>
      {open && children}
    </div>
  );
}

function NotabilityBadge({ n }: { n: NotabilityResult }) {
  const color = n.score >= 0.7 ? "var(--success)" : n.score >= 0.4 ? "var(--warning)" : "var(--danger)";
  return <span style={{ fontSize: 12, color, fontWeight: 600, marginTop: 2, display: "inline-block" }}>{n.label} · {n.rs_count} RS source{n.rs_count !== 1 ? "s" : ""}</span>;
}

function NotabilityCard({ n }: { n: NotabilityResult }) {
  const bg = n.score >= 0.7 ? "#dcfce7" : n.score >= 0.4 ? "#fef9c3" : "#fee2e2";
  const border = n.score >= 0.7 ? "#86efac" : n.score >= 0.4 ? "#fde047" : "#fca5a5";
  return (
    <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 8, padding: "12px 16px" }}>
      <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Notability: {n.label}</p>
      <p style={{ fontSize: 12 }}>{n.rs_count} reliable secondary source{n.rs_count !== 1 ? "s" : ""}</p>
      <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>{n.reason}</p>
    </div>
  );
}

function ChecklistCard({ profile, wikiStatus }: { profile: PersonProfile; wikiStatus: WikiStatus }) {
  const rsCount = profile.notability?.rs_count ?? 0;
  const verifiedCount = profile.claims.filter(c => c.verification === "confirmed" || c.verification === "edited").length;
  const humanVerifiedSources = profile.sources.filter(s => s.human_verified).length;
  const items = [
    { done: rsCount >= 2, label: `2+ RS sources (${rsCount} found)` },
    { done: humanVerifiedSources > 0, label: `Sources checked (${humanVerifiedSources}/${profile.sources.length})` },
    { done: verifiedCount > 0, label: `Claims verified (${verifiedCount}/${profile.claims.length})` },
    { done: wikiStatus.status !== "exists", label: "No existing Wikipedia article" },
    { done: wikiStatus.status !== "deleted", label: "No prior deletion" },
  ];
  return (
    <div className="card">
      <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>AfC checklist</p>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7, fontSize: 12 }}>
          <span style={{ color: item.done ? "var(--success)" : "var(--muted)", fontWeight: 700 }}>
            {item.done ? "✓" : "·"}
          </span>
          <span style={{ color: item.done ? "var(--text)" : "var(--muted)" }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}

function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      padding: "12px 16px", border: "none", borderRadius: 0, background: "transparent",
      fontWeight: active ? 700 : 400,
      borderBottom: active ? "2px solid var(--primary)" : "2px solid transparent",
      color: active ? "var(--primary)" : "var(--muted)",
      fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 4,
    }}>
      {children}
    </button>
  );
}
