import { useState } from "react";
import type { PersonProfile } from "../types";
import { addDocumentFact, targetedSearch } from "../api";

export function ProfileTab({ profile, onProfileUpdate }: {
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

