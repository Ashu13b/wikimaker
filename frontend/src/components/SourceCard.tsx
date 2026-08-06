import { useState } from "react";
import type { Source, Claim, NotabilityResult, UrlSuggestion } from "../types";
import { verifySource, rejectSource } from "../api";
import { getHostname } from "../url";

export function SourceCard({ source, sourceNumber, profileName, linkOpened, onLinkOpen, onVerified, onRejected, onVerifyingChange, allClaims }: {
  source: Source;
  sourceNumber: number;
  profileName: string;
  linkOpened: boolean;
  onLinkOpen: () => void;
  onVerified: (v: boolean, newClaims?: Claim[], missingSlots?: string[]) => void;
  onRejected: (result: { sources: Source[]; claims: Claim[]; notability: NotabilityResult }) => void;
  onVerifyingChange?: (verifying: boolean) => void;
  allClaims?: Claim[];
}) {
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [rejecting, setRejecting] = useState(false);

  const tagClass = SOURCE_TAG_CLASS;
  const tagLabel = SOURCE_TAG_LABEL;

  const sourceClaims = (allClaims ?? []).filter(c => c.source_url === source.url);

  async function handleVerify() {
    setVerifying(true);
    setVerifyError(null);
    onVerifyingChange?.(true);
    try {
      const resp = await verifySource(profileName, source.url, !source.human_verified);
      onVerified(!source.human_verified, resp.new_claims ?? [], resp.missing_slots ?? []);
    } catch (e) {
      setVerifyError(String(e));
    } finally {
      setVerifying(false);
      onVerifyingChange?.(false);
    }
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
            {source.publisher || getHostname(source.url)}
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

      {verifyError && (
        <p style={{ fontSize: 12, color: "var(--danger)", marginTop: 8 }}>{verifyError}</p>
      )}

      {/* Inline Extracted Claims — AI suggestions, not yet verified facts */}
      {sourceClaims.length > 0 && (
        <div style={{ marginTop: 10, padding: "8px 12px", background: "rgba(139, 92, 246, 0.07)", border: "1px solid rgba(139, 92, 246, 0.2)", borderRadius: 6 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: "#7c3aed", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>
            Suggested claims ({sourceClaims.length})
          </p>
          {sourceClaims.map((c, idx) => (
            <div key={idx} style={{ fontSize: 12, color: "var(--text)", marginBottom: 4, display: "flex", gap: 6, alignItems: "baseline" }}>
              <span style={{ fontWeight: 700, textTransform: "uppercase", fontSize: 10, color: "var(--muted)", marginRight: 2, flexShrink: 0 }}>{c.field}</span>
              <span>{c.text}</span>
              <span style={{ fontSize: 10, fontWeight: 700, color: c.verification === "confirmed" || c.verification === "edited" ? "var(--success)" : "var(--warning)", flexShrink: 0 }}>
                {c.draft_approved ? "· in draft" : c.verification === "unverified" ? "· unverified" : `· ${c.verification}`}
              </span>
            </div>
          ))}
          <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>
            These were extracted by the AI — verifying the source does <strong>not</strong> put them in the draft. Confirm or edit them in the Claims tab, then press + to include.
          </p>
        </div>
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
            {verifying ? "Extracting claims…" : source.human_verified ? `✓ Verified${sourceClaims.length ? ` · ${sourceClaims.length} claim${sourceClaims.length === 1 ? "" : "s"} suggested` : ""}` : "Confirm & extract claims"}
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


export function RelevanceBadge({ flag }: { flag: Source["relevance_flag"] }) {
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

export function FetchedByTag({ fetchedBy, userProvided }: { fetchedBy: Source["fetched_by"]; userProvided: boolean }) {
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

export function AuthorMatchBadge({ source }: { source: Source }) {
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

