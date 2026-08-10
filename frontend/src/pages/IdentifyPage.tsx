import { useState, useEffect } from "react";
import { identifyPerson, listSessions, resumeSession, deleteSession, type SessionSummary, type IdentifyResult } from "../api";
import type { PersonCandidate, PersonProfile, WikiStatus } from "../types";

interface Props {
  onConfirmed: (candidate: PersonCandidate) => void;
  onResume: (profile: PersonProfile, wikiStatus: WikiStatus) => void;
}

type View = "form" | "preview";

export default function IdentifyPage({ onConfirmed, onResume }: Props) {
  const [view, setView] = useState<View>("form");

  // Form fields
  const [name, setName] = useState("");
  const [field, setField] = useState("");
  const [affiliation, setAffiliation] = useState("");
  const [nationality, setNationality] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");

  // Search preview
  const [searching, setSearching] = useState(false);
  const [previewResults, setPreviewResults] = useState<IdentifyResult[]>([]);
  const [wikiStatus, setWikiStatus] = useState<import("../types").WikiStatus | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const identityMatches = previewResults.filter(r => r.kind === "identity");
  const webClues = previewResults.filter(r => r.kind !== "identity");

  const wikiChip = wikiStatus ? {
    exists: { bg: "#eff6ff", border: "#93c5fd", color: "#1d4ed8", text: "An English Wikipedia article already exists — research will propose improvements, not a new draft.", url: wikiStatus.url },
    draft: { bg: "#fffbeb", border: "#fcd34d", color: "#92400e", text: "A draft already exists at AfC — research will improve it rather than create a competing one.", url: wikiStatus.url },
    deleted: { bg: "#fef2f2", border: "#fca5a5", color: "#b91c1c", text: "A previous deletion was found — review its history before considering another draft.", url: wikiStatus.url },
    clear: { bg: "#f0fdf4", border: "#86efac", color: "#15803d", text: "No article or draft found — research will build evidence for a new AfC draft.", url: null },
  }[wikiStatus.status] : null;

  // Sessions
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [resumeLoading, setResumeLoading] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
  }, []);

  async function handleResume(file: string, id: string | null) {
    setResumeLoading(file);
    try {
      const result = await resumeSession(id ?? file);
      onResume(result.profile, result.wiki_status);
    } catch (e) {
      setSessionError(String(e));
    } finally {
      setResumeLoading(null);
    }
  }

  async function handleDelete(file: string, id: string | null) {
    setDeleteLoading(file);
    try {
      await deleteSession(id ?? file);
      setSessions(prev => prev.filter(s => s.file !== file));
      setDeleteConfirm(null);
    } catch (e) {
      setSessionError(String(e));
    } finally {
      setDeleteLoading(null);
    }
  }

  async function handleSearch() {
    if (!name.trim()) return;
    setSearching(true);
    setSearchError(null);
    try {
      const data = await identifyPerson(name.trim(), field.trim() || null, affiliation.trim() || null);
      setPreviewResults(data.results);
      setWikiStatus(data.wiki_status);
      setView("preview");
    } catch (e) {
      setSearchError(String(e));
    } finally {
      setSearching(false);
    }
  }

  function handleConfirm() {
    onConfirmed({
      name: name.trim(),
      photo_url: photoUrl.trim() || null,
      bio_snippet: [field, affiliation, nationality].filter(Boolean).join(" · "),
      birth_year: null,
      nationality: nationality.trim() || null,
      field: field.trim() || null,
      affiliation: affiliation.trim() || null,
      wikipedia_url: null,
      wikidata_id: null,
    });
  }

  function handleConfirmIdentity(r: IdentifyResult) {
    setField(r.field ?? field);
    setAffiliation(r.affiliation ?? affiliation);
    setNationality(r.nationality ?? nationality);
    setPhotoUrl(r.photo_url ?? photoUrl);
    onConfirmed({
      name: name.trim(),
      photo_url: r.photo_url || photoUrl.trim() || null,
      bio_snippet: r.snippet || [field, affiliation, nationality].filter(Boolean).join(" · "),
      birth_year: r.birth_year || null,
      nationality: r.nationality || nationality.trim() || null,
      field: r.field || field.trim() || null,
      affiliation: r.affiliation || affiliation.trim() || null,
      wikipedia_url: r.wikipedia_url || null,
      wikidata_id: r.wikidata_id || null,
    });
  }

  return (
    <main className="subject-start-page">
      <div style={{ textAlign: "center", marginBottom: 36 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>Wikimaker</h1>
        <p style={{ color: "var(--muted)", fontSize: 15 }}>
          Research a person, check their Wikimedia status, and build the right output.
        </p>
      </div>

      {/* Saved sessions */}
      {sessions.length > 0 && view === "form" && (
        <div style={{ marginBottom: 28 }}>
          <p style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", marginBottom: 10, textTransform: "uppercase", letterSpacing: 0.5 }}>
            Resume research
          </p>
          {sessionError && <p style={{ color: "var(--danger)", fontSize: 13, marginBottom: 10 }}>{sessionError}</p>}
          {sessions.map(s => (
            <div key={s.file} className="card" style={{ marginBottom: 10, padding: "14px 18px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                {s.photo_url ? (
                  <img src={s.photo_url} alt={s.name}
                    style={{ width: 40, height: 40, borderRadius: 6, objectFit: "cover", border: "1px solid var(--border)", flexShrink: 0 }} />
                ) : (
                  <div style={{
                    width: 40, height: 40, borderRadius: 6, background: "var(--bg)",
                    border: "1px solid var(--border)", flexShrink: 0,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 16, fontWeight: 700, color: "var(--primary)",
                  }}>
                    {s.name[0]}
                  </div>
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontWeight: 700, fontSize: 14, marginBottom: 2 }}>{s.name}</p>
                  <p style={{ fontSize: 12, color: "var(--muted)" }}>
                    {[s.field, s.affiliation].filter(Boolean).join(" · ")}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
                    {s.source_count} sources · {s.claim_count} claims · {s.notability_label}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  <button className="btn-primary" onClick={() => handleResume(s.file, s.id)} disabled={resumeLoading === s.file}
                    style={{ fontSize: 13, padding: "8px 16px" }}>
                    {resumeLoading === s.file ? "Loading…" : "Resume →"}
                  </button>
                  <button onClick={() => setDeleteConfirm(s.file)} disabled={deleteLoading === s.file}
                    title="Delete session"
                    style={{ padding: "8px 10px", fontSize: 14, borderRadius: 6, border: "1px solid var(--border)", background: "transparent", color: "var(--muted)", cursor: "pointer" }}>
                    ✕
                  </button>
                </div>
              </div>
              {deleteConfirm === s.file && (
                <div style={{ marginTop: 12, padding: "10px 12px", background: "#fff5f5", border: "1px solid #fca5a5", borderRadius: 8, display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 13, flex: 1, color: "var(--danger)" }}>Delete "{s.name}"? This cannot be undone.</span>
                  <button onClick={() => handleDelete(s.file, s.id)} disabled={deleteLoading === s.file}
                    style={{ padding: "6px 14px", fontSize: 12, fontWeight: 700, borderRadius: 6, border: "none", background: "var(--danger)", color: "#fff", cursor: "pointer" }}>
                    {deleteLoading === s.file ? "Deleting…" : "Delete"}
                  </button>
                  <button onClick={() => setDeleteConfirm(null)}
                    style={{ padding: "6px 12px", fontSize: 12, borderRadius: 6, border: "1px solid var(--border)", background: "transparent", cursor: "pointer" }}>
                    Cancel
                  </button>
                </div>
              )}
            </div>
          ))}
          <div style={{ borderTop: "1px solid var(--border)", marginTop: 20, paddingTop: 20 }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", marginBottom: 14, textTransform: "uppercase", letterSpacing: 0.5 }}>
              New subject research
            </p>
          </div>
        </div>
      )}

      {/* Step 1 — form */}
      {view === "form" && (
        <div className="card">
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 14 }}>Name</label>
            <input value={name} onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleConfirm()}
              placeholder="e.g. Prem Singh Yadav" autoFocus />
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
              Field / profession <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span>
            </label>
            <input value={field} onChange={e => setField(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleConfirm()}
              placeholder="e.g. Animal biotechnology, Buffalo cloning" />
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
              Institution <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional — helps find the right person)</span>
            </label>
            <input value={affiliation} onChange={e => setAffiliation(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleConfirm()}
              placeholder="e.g. ICAR-CIRB, Hisar, Haryana" />
          </div>
          <details className="optional-subject-details">
            <summary>More optional details</summary>
            <div style={{ marginTop: 14, marginBottom: 14 }}>
              <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 13 }}>Nationality</label>
              <input value={nationality} onChange={e => setNationality(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleConfirm()}
                placeholder="e.g. Indian" />
            </div>
            <div style={{ marginBottom: 4 }}>
              <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 13 }}>Photo URL</label>
              <input value={photoUrl} onChange={e => setPhotoUrl(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleConfirm()}
                placeholder="https://…/photo.jpg" />
            </div>
          </details>
          {searchError && <p style={{ color: "var(--danger)", fontSize: 13, marginBottom: 12 }}>{searchError}</p>}
          <div className="subject-actions">
            <button className="btn-primary" onClick={handleConfirm}
              disabled={!name.trim()} style={{ flex: 1 }}>
              Start research →
            </button>
            <button className="btn-ghost" onClick={handleSearch}
              disabled={searching || !name.trim()} style={{ flex: 1 }}>
              {searching ? "Searching…" : "Preview identity clues"}
            </button>
          </div>
          <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 10, lineHeight: 1.45 }}>
            An existing Wikipedia article or Wikidata item is not required. Web matches are optional clues for avoiding same-name mistakes.
          </p>
        </div>
      )}

      {/* Step 2 — preview */}
      {view === "preview" && (
        <div>
          <div style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <p style={{ fontWeight: 700, fontSize: 15, marginBottom: 2 }}>{name}</p>
              <p style={{ fontSize: 13, color: "var(--muted)" }}>
                {[field, affiliation].filter(Boolean).join(" · ")}
              </p>
            </div>
            <button className="btn-ghost" onClick={() => setView("form")} style={{ fontSize: 13 }}>
              ← Edit details
            </button>
          </div>

          {wikiChip && (
            <div style={{ marginBottom: 16, padding: "10px 14px", borderRadius: 8, background: wikiChip.bg, border: `1px solid ${wikiChip.border}`, color: wikiChip.color, fontSize: 13, lineHeight: 1.5 }}>
              {wikiChip.text}
              {wikiChip.url && (
                <> <a href={wikiChip.url} target="_blank" rel="noreferrer" style={{ color: wikiChip.color, textDecoration: "underline", fontWeight: 600 }}>Open ↗</a></>
              )}
            </div>
          )}

          {previewResults.length === 0 ? (
            <div className="card" style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 13, color: "var(--muted)" }}>
                No identity clues found yet. This does not prevent research or mean the subject is ineligible for Wikipedia.
                You can continue and add authoritative sources manually.
              </p>
            </div>
          ) : (
            <div style={{ marginBottom: 16 }}>
              {identityMatches.length > 0 && (
                <>
                  <p style={{ fontSize: 12, fontWeight: 700, color: "var(--primary)", marginBottom: 10, textTransform: "uppercase", letterSpacing: 0.5 }}>
                    Wikipedia/Wikidata identity match — confirm this person
                  </p>
                  {identityMatches.map((r, i) => (
                    <div key={i} className="card" style={{ marginBottom: 10, padding: "12px 16px" }}>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                        {r.photo_url && (
                          <img src={r.photo_url} alt={r.title}
                            style={{ width: 48, height: 48, borderRadius: 6, objectFit: "cover", border: "1px solid var(--border)", flexShrink: 0 }} />
                        )}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontWeight: 700, fontSize: 14, marginBottom: 3 }}>{r.title}</p>
                          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 5, lineHeight: 1.45 }}>
                            {r.snippet.slice(0, 220)}{r.snippet.length > 220 ? "…" : ""}
                          </p>
                          <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>
                            {[r.nationality, r.field, r.affiliation, r.birth_year].filter(Boolean).join(" · ") || r.publisher}
                          </p>
                          <button className="btn-primary" onClick={() => handleConfirmIdentity(r)}
                            style={{ fontSize: 13, padding: "7px 16px" }}>
                            Confirm this person →
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}

              {webClues.length > 0 && (
                <>
                  <p style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", marginTop: identityMatches.length > 0 ? 18 : 0, marginBottom: 10, textTransform: "uppercase", letterSpacing: 0.5 }}>
                    Possible identity clues — confirm independently
                  </p>
                  {webClues.map((r, i) => (
                    <div key={i} className="card" style={{ marginBottom: 10, padding: "12px 16px" }}>
                      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontWeight: 600, fontSize: 13, marginBottom: 3 }}>{r.title}</p>
                          <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 5 }}>
                            {r.snippet.slice(0, 180)}{r.snippet.length > 180 ? "…" : ""}
                          </p>
                          <a href={r.url} target="_blank" rel="noreferrer"
                            style={{ fontSize: 11, color: "var(--primary)" }}>
                            {r.publisher} ↗
                          </a>
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn-primary" onClick={handleConfirm} style={{ flex: 1 }}>
              Start research for {name} →
            </button>
          </div>
          <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 10, textAlign: "center" }}>
            These preview results are clues only. Research will discover and classify candidate sources separately.
          </p>
        </div>
      )}
    </main>
  );
}
