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
  const [searchError, setSearchError] = useState<string | null>(null);

  // Sessions
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [resumeLoading, setResumeLoading] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
  }, []);

  async function handleResume(file: string) {
    setResumeLoading(file);
    try {
      const result = await resumeSession(file);
      onResume(result.profile, result.wiki_status);
    } catch (e) {
      setSessionError(String(e));
    } finally {
      setResumeLoading(null);
    }
  }

  async function handleDelete(file: string) {
    setDeleteLoading(file);
    try {
      await deleteSession(file);
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
      const results = await identifyPerson(name.trim(), field.trim() || null, affiliation.trim() || null);
      setPreviewResults(results);
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

  return (
    <div style={{ maxWidth: 580, margin: "60px auto", padding: "0 20px" }}>
      <div style={{ textAlign: "center", marginBottom: 36 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>Wikimaker</h1>
        <p style={{ color: "var(--muted)", fontSize: 15 }}>
          Research a person and generate a Wikipedia AfC draft.
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
                  <button className="btn-primary" onClick={() => handleResume(s.file)} disabled={resumeLoading === s.file}
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
                  <button onClick={() => handleDelete(s.file)} disabled={deleteLoading === s.file}
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
              New research
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
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="e.g. Prem Singh Yadav" autoFocus />
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
              Field / profession <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span>
            </label>
            <input value={field} onChange={e => setField(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="e.g. Animal biotechnology, Buffalo cloning" />
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
              Institution <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional — helps find the right person)</span>
            </label>
            <input value={affiliation} onChange={e => setAffiliation(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="e.g. ICAR-CIRB, Hisar, Haryana" />
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
              Nationality <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span>
            </label>
            <input value={nationality} onChange={e => setNationality(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="e.g. Indian" />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
              Photo URL <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span>
            </label>
            <input value={photoUrl} onChange={e => setPhotoUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="https://…/photo.jpg" />
          </div>
          {searchError && <p style={{ color: "var(--danger)", fontSize: 13, marginBottom: 12 }}>{searchError}</p>}
          <button className="btn-primary" onClick={handleSearch}
            disabled={searching || !name.trim()} style={{ width: "100%" }}>
            {searching ? "Searching…" : "Find person →"}
          </button>
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

          {previewResults.length === 0 ? (
            <div className="card" style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 13, color: "var(--muted)" }}>
                No web results found yet — this person may not have a strong online presence.
                You can still start research and add sources manually.
              </p>
            </div>
          ) : (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", marginBottom: 10, textTransform: "uppercase", letterSpacing: 0.5 }}>
                Web results found for this person
              </p>
              {previewResults.map((r, i) => (
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
            </div>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn-primary" onClick={handleConfirm} style={{ flex: 1 }}>
              Yes, research {name} →
            </button>
          </div>
          <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 10, textAlign: "center" }}>
            These sources will be included in the research automatically.
          </p>
        </div>
      )}
    </div>
  );
}
