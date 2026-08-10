import { useState, useEffect } from "react";
import type { PersonProfile, Source, UrlSuggestion } from "../types";
import { addSource, addSourcePaste, deepCrawl, getSession, findResearcherIds, refreshPapers, fetchFromBrowser, fetchBlockedSources, suggestUrls, skipSuggestion, profileRef } from "../api";
import { normalizeUrl } from "../url";
import { SourceCard } from "./SourceCard";
import { Expander } from "./WorkspaceCards";
import BookmarkletCard from "./BookmarkletCard";
import { ResearcherIdsStrip } from "./ProfileTab";

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


export function SourcesPanel({ profile, openedLinks, onLinkOpen, onProfileUpdate, relayPending, onRelayConsumed, onOperationStatusChange, showBrowser, setShowBrowser }: {
  profile: PersonProfile;
  openedLinks: Set<string>;
  onLinkOpen: (url: string) => void;
  onProfileUpdate: (p: PersonProfile) => void;
  relayPending?: { url: string; text: string } | null;
  onRelayConsumed?: () => void;
  onOperationStatusChange?: (op: string, active: boolean) => void;
  showBrowser?: boolean;
  setShowBrowser?: (v: boolean) => void;
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
  const [sentToBrowser, setSentToBrowser] = useState(false);
  const [browserFetchLoading, setBrowserFetchLoading] = useState(false);

  const [suggestions, setSuggestions] = useState<UrlSuggestion[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const [skipped, setSkipped] = useState<Set<string>>(new Set());

  const [idsLoading, setIdsLoading] = useState(false);
  const [idsError, setIdsError] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const [pipelineMsg, setPipelineMsg] = useState<string | null>(null);

  // Wiki+ relay: auto-fill the paste form with the relayed page, then consume.
  useEffect(() => {
    if (!relayPending) return;
    setPasteUrl(relayPending.url);
    setPasteText(relayPending.text);
    setExpandPaste(true);
    onRelayConsumed?.();
  }, [relayPending, onRelayConsumed]);

  // Keep the sidebar Research operations card in sync with in-flight work.
  useEffect(() => { onOperationStatusChange?.("suggester", suggestionsLoading); }, [suggestionsLoading]);
  useEffect(() => { onOperationStatusChange?.("extractor", urlLoading || pasteLoading || browserFetchLoading); }, [urlLoading, pasteLoading, browserFetchLoading]);
  useEffect(() => { onOperationStatusChange?.("crawler", crawlLoading); }, [crawlLoading]);
  useEffect(() => { onOperationStatusChange?.("idSync", idsLoading || refreshingId !== null); }, [idsLoading, refreshingId]);

  async function loadSuggestions() {
    setSuggestionsLoading(true); setSuggestionsError(null);
    try {
      const results = await suggestUrls(profileRef(profile));
      setSuggestions(results);
      setSkipped(new Set());
    } catch (e) { setSuggestionsError(String(e)); }
    finally { setSuggestionsLoading(false); }
  }

  useEffect(() => { loadSuggestions(); }, [profileRef(profile)]);

  async function handleApproveSuggestion(url: string) {
    setUrlInput(url);
    setSkipped(s => new Set([...s, url])); // hide from queue immediately
    setUrlLoading(true); setUrlError(null); setBlockedUrl(null); setPipelineMsg(null); setSentToBrowser(false);
    try {
      const resp = await addSource(profileRef(profile), url);
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

  const isDuplicate = urlInput.trim() !== "" && profile.sources.some(s => normalizeUrl(s.url) === normalizeUrl(urlInput));

  async function handleAddUrl() {
    if (!urlInput.trim() || isDuplicate) return;
    setUrlLoading(true); setUrlError(null); setBlockedUrl(null); setPipelineMsg(null); setSentToBrowser(false);
    try {
      const resp = await addSource(profileRef(profile), urlInput.trim());
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
      const resp = await addSourcePaste(profileRef(profile), pasteUrl.trim(), pasteText.trim());
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
      const resp = await deepCrawl(profileRef(profile), seeds, keywords);
      const updated = await getSession(profileRef(profile));
      onProfileUpdate(updated);
      setCrawlResult(`Crawled ${resp.nodes_crawled} pages · ${resp.relevant_sources} relevant sources · ${resp.new_claims} new claims`);
      setCrawlSeeds(""); setCrawlKeywords("");
    } catch (e) { setCrawlError(String(e)); }
    finally { setCrawlLoading(false); }
  }

  async function handleFetchFromBrowser() {
    setBrowserFetchLoading(true);
    try {
      const resp = await fetchFromBrowser(profileRef(profile));
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

  async function handleAutoFetchBlocked() {
    setBrowserFetchLoading(true); setUrlError(null); setPipelineMsg(null);
    try {
      const resp = await fetchBlockedSources(profileRef(profile));
      if (resp.profile) {
        onProfileUpdate({ ...resp.profile, notability: resp.notability ?? null });
      } else {
        const updated = await getSession(profileRef(profile));
        onProfileUpdate(updated);
      }
      if (resp.walls.length > 0) {
        await fetch("/browser/navigate", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: resp.walls[0] }),
        });
        if (!showBrowser && setShowBrowser) setShowBrowser(true);
        setBlockedUrl(resp.walls[0]);
        setSentToBrowser(true);
        setUrlError(`Paused at a bot wall: ${resp.walls[0]} — solve it, then tap Import current page.`);
      } else if (resp.fetched.length > 0) {
        setPipelineMsg(`Auto-fetched ${resp.fetched.length} blocked source(s) via the browser.`);
      }
    } catch (e) { setUrlError(String(e)); }
    finally { setBrowserFetchLoading(false); }
  }

  async function handleFindIds() {
    setIdsLoading(true); setIdsError(null);
    try {
      const resp = await findResearcherIds(profileRef(profile));
      onProfileUpdate({ ...profile, researcher_ids: resp.researcher_ids, confirmed_ids: resp.confirmed_ids });
    } catch (e) { setIdsError(String(e)); }
    finally { setIdsLoading(false); }
  }

  async function handleRefreshPapers(idType: string, idValue: string, confirm?: boolean) {
    setRefreshingId(idType); setIdsError(null);
    try {
      const resp = await refreshPapers(profileRef(profile), idType, idValue, confirm);
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

  const visibleSuggestions = suggestions.filter(s => {
    const normUrl = normalizeUrl(s.url);
    const isSkipped = Array.from(skipped).some(sk => normalizeUrl(sk) === normUrl);
    const isAlreadySourced = profile.sources.some(src => normalizeUrl(src.url) === normUrl);
    return !isSkipped && !isAlreadySourced;
  });

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
            {profile.sources.some(s => s.liveness === "blocked") && (
              <button onClick={handleAutoFetchBlocked} disabled={browserFetchLoading} title="Walk every blocked source through the remote browser automatically; stops only at a real CAPTCHA" style={{ fontSize: 12, background: "none", border: "1px solid #f59e0b", borderRadius: 6, padding: "3px 10px", cursor: "pointer", color: "#92400e" }}>
                {browserFetchLoading ? "Fetching…" : "Auto-fetch blocked"}
              </button>
            )}
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
                await fetch("/browser/navigate", {
                  method: "POST", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ url: s.url }),
                });
                if (!showBrowser && setShowBrowser) {
                  setShowBrowser(true);
                }
              } catch { window.open(s.url, "_blank"); }
            }

            return (
              <div key={s.url} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "10px 12px", background: "var(--surface-dim, var(--bg))" }}>
                <div className="suggestion-row" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
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
                      {s.source_type && (() => {
                        const stConfig: Record<string, { icon: string; color: string; label: string }> = {
                          profile: { icon: "👤", color: "#8b5cf6", label: "Profile" },
                          publication: { icon: "📄", color: "#0369a1", label: "Publication" },
                          news: { icon: "📰", color: "#b45309", label: "News" },
                        };
                        const cfg = stConfig[s.source_type] ?? stConfig.news;
                        return (
                          <span style={{ fontSize: 10, borderRadius: 4, padding: "1px 6px", fontWeight: 700, background: `${cfg.color}15`, color: cfg.color, border: `1px solid ${cfg.color}35` }}>
                            {cfg.icon} {cfg.label}
                          </span>
                        );
                      })()}
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
                    <button onClick={async () => {
                      setSkipped(sk => new Set([...sk, s.url]));
                      try {
                        await skipSuggestion(profileRef(profile), s.url);
                      } catch (e) {
                        console.error("Failed to skip suggestion:", e);
                      }
                    }} style={{ fontSize: 12, padding: "4px 12px", background: "none", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", color: "var(--muted)" }}>
                      Skip
                    </button>
                  </div>
                </div>
                {s.snippet && (
                  <p style={{ fontSize: 11, color: "var(--muted)", margin: "6px 0 0", lineHeight: 1.4, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                    {s.snippet.startsWith("Found on: ") ? (
                      <>
                        Found on:{" "}
                        <a href={s.snippet.replace("Found on: ", "")} target="_blank" rel="noreferrer" style={{ color: "var(--primary)", textDecoration: "underline" }}>
                          {s.snippet.replace("Found on: ", "")}
                        </a>
                      </>
                    ) : (
                      s.snippet
                    )}
                  </p>
                )}
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
      </div>

      {/* Add-source tools — manual URL (fallback) always visible, niche tools expandable */}
      <div className="card" style={{ borderTopLeftRadius: 0, borderTopRightRadius: 0, marginBottom: 16 }}>
        <p style={{ fontSize: 13, fontWeight: 600, margin: "0 0 10px" }}>Add a source</p>
        <div style={{ display: "flex", gap: 8 }}>
          <input value={urlInput} onChange={e => setUrlInput(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddUrl()} placeholder="Paste a URL: ORCID, Scholar, institutional profile, paper…" style={{ flex: 1, borderColor: isDuplicate ? "var(--warning)" : undefined }} />
          <button className="btn-primary" onClick={handleAddUrl} disabled={urlLoading || !urlInput.trim() || isDuplicate}>{urlLoading ? "Fetching…" : "Add"}</button>
        </div>
        {isDuplicate && <p style={{ color: "var(--warning)", fontSize: 12, marginTop: 6 }}>Already in your sources list.</p>}

        <div style={{ marginTop: 8 }}>
          <Expander label="Paste text from blocked page / PDF" open={expandPaste} onToggle={() => setExpandPaste(v => !v)}>
            <div style={{ marginTop: 10 }}>
              <BookmarkletCard />
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

      {/* Confirmed sources */}
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
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
              <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>Sources in this session</p>
              <span style={{ fontSize: 11, color: "var(--muted)" }}>verify each source, then approve its claims in the Claims tab</span>
            </div>
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
                profileName={profileRef(profile)}
                linkOpened={openedLinks.has(s.url)}
                allClaims={profile.claims}
                onLinkOpen={() => onLinkOpen(s.url)}
                onVerified={(verified, newClaims, missingSlots) => {
                  const sources = profile.sources.map(src => src.url === s.url ? { ...src, human_verified: verified } : src);
                  const freshClaims = newClaims ? newClaims.filter(c => !profile.claims.some(ex => ex.source_url === c.source_url && ex.text === c.text)) : [];
                  onProfileUpdate({
                    ...profile,
                    sources,
                    claims: [...profile.claims, ...freshClaims],
                    missing_slots: missingSlots ?? profile.missing_slots,
                  });
                  // New profile_links may have been extracted from this source — refresh queue
                  if (verified) loadSuggestions();
                }}
                onAssessed={(updatedSource, notability) => {
                  onProfileUpdate({
                    ...profile,
                    sources: profile.sources.map(src => src.url === updatedSource.url ? updatedSource : src),
                    notability,
                  });
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

