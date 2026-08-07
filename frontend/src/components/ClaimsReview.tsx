import { useState } from "react";
import type { Claim, PersonProfile } from "../types";
import { verifyClaim } from "../api";

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

type FilterTab = "all" | "draft" | "review" | "unsourced";

export default function ClaimsReview({ claims, allClaims, profile, onProfileUpdate, emptyMessage }: {
  claims: Claim[];
  allClaims: Claim[];
  profile: PersonProfile;
  onProfileUpdate: (p: PersonProfile) => void;
  emptyMessage: string;
}) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [loading, setLoading] = useState<number | null>(null);
  const [tab, setTab] = useState<FilterTab>(() => claims.some(c => !c.draft_approved && c.verification !== "skipped") ? "review" : "all");

  const draftCount = claims.filter(c => c.draft_approved).length;
  const unsourcedCount = claims.filter(c => !c.source_url).length;
  const needsReviewCount = claims.filter(c => !c.draft_approved && c.verification !== "skipped").length;

  const visible = tab === "all" ? claims
    : tab === "draft" ? claims.filter(c => c.draft_approved)
    : tab === "unsourced" ? claims.filter(c => !c.source_url)
    : claims.filter(c => !c.draft_approved && c.verification !== "skipped");

  const tabs: { id: FilterTab; label: string; count: number }[] = [
    { id: "all", label: "All", count: claims.length },
    { id: "draft", label: "In draft", count: draftCount },
    { id: "review", label: "Needs review", count: needsReviewCount },
    { id: "unsourced", label: "Unsourced", count: unsourcedCount },
  ];

  if (claims.length === 0) {
    return <p style={{ fontSize: 13, color: "var(--muted)", padding: "20px 0" }}>{emptyMessage}</p>;
  }

  async function doVerify(globalIndex: number, action: "confirm" | "edit" | "skip" | "approve_draft" | "remove_draft", text?: string) {
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
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", paddingBottom: 12 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{
              fontSize: 12, padding: "5px 11px", borderRadius: 999, cursor: "pointer",
              border: tab === t.id ? "1px solid var(--primary)" : "1px solid var(--border)",
              background: tab === t.id ? "rgba(37, 99, 235, 0.1)" : "var(--bg)",
              color: tab === t.id ? "var(--primary)" : "var(--muted)", fontWeight: tab === t.id ? 700 : 500,
            }}>
            {t.label} <span style={{ opacity: 0.75 }}>({t.count})</span>
          </button>
        ))}
        <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: "auto" }}>
          {draftCount} of {claims.length} claims included in draft · only claims with a verified source can be added
        </span>
      </div>

      {visible.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--muted)", padding: "16px 0" }}>
          {tab === "draft" ? "No claims included in the draft yet. Confirm a claim, then press + to include it." :
           tab === "unsourced" ? "No unsourced claims." :
           tab === "review" ? "Nothing waiting for review." : emptyMessage}
        </p>
      ) : (
        <div>
        {visible.map(claim => {
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
                <div style={{ display: "flex", gap: 6, marginBottom: 5, flexWrap: "wrap", alignItems: "center" }}>
                  <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--muted)" }}>
                    {claim.field}
                  </span>
                  {claim.provenance_status === "verified_independent" && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "rgba(16, 185, 129, 0.15)", color: "#10b981" }}>
                      Independent Secondary
                    </span>
                  )}
                  {claim.provenance_status === "primary_sourced" && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" }}>
                      Primary Sourced
                    </span>
                  )}
                  {claim.trust_score !== undefined && (
                    <span style={{ fontSize: 10, fontWeight: 600, color: claim.trust_score >= 0.7 ? "var(--success)" : "var(--muted)" }}>
                      · {Math.round(claim.trust_score * 100)}% Trust
                    </span>
                  )}
                  {claim.verification !== "unverified" && (
                    <span style={{ fontSize: 11, fontWeight: 700, color: verificationColor[claim.verification] }}>
                      · {claim.verification}
                    </span>
                  )}
                  {claim.draft_approved && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "rgba(37, 99, 235, 0.12)", color: "var(--primary)" }}>
                      Included in draft
                    </span>
                  )}
                  {claim.user_provided && (
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>· manual entry</span>
                  )}
                  {!claim.user_provided && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "rgba(139, 92, 246, 0.12)", color: "#7c3aed" }}>
                      AI-suggested · review
                    </span>
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
                <div style={{ display: "flex", flexDirection: "column", gap: 4, flexShrink: 0 }}>
                  <ActionBtn onClick={() => { setEditingIndex(globalIndex); setEditText(claim.text); }} disabled={isLoading} color="var(--primary)" title="Edit claim">✎</ActionBtn>
                  <ActionBtn
                    onClick={() => doVerify(globalIndex, claim.draft_approved ? "remove_draft" : "approve_draft")}
                    disabled={isLoading}
                    color={claim.draft_approved ? "var(--danger)" : "var(--success)"}
                    title={claim.draft_approved ? "Remove from draft" : "Include in draft"}
                  >
                    {claim.draft_approved ? "−" : "+"}
                  </ActionBtn>
                </div>
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
      )}
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
