import { useState } from "react";
import type { Claim, PersonProfile } from "../types";
import { verifyClaim, batchVerifyClaims, profileRef } from "../api";
import { safeHref } from "../url";
import { SOURCE_TAG_CLASS, SOURCE_TAG_LABEL } from "./slotMeta";

type FilterTab = "all" | "review" | "draft" | "dossier" | "unsourced" | "corroborated";

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
  const [batchLoading, setBatchLoading] = useState<string | null>(null);
  const [tab, setTab] = useState<FilterTab>(() => claims.some(c => c.verification === "unverified") ? "review" : "all");

  const draftCount = claims.filter(c => c.draft_approved).length;
  const dossierCount = claims.filter(c => (c.verification === "confirmed" || c.verification === "edited") && !c.draft_approved).length;
  const unsourcedCount = claims.filter(c => !c.source_url).length;
  const needsReviewCount = claims.filter(c => c.verification === "unverified").length;
  const corroboratedIndices = new Set(
    profile.saturation?.corroborated_clusters?.flatMap(c => c.claim_indices) ?? []
  );
  const corroboratedCount = claims.filter(c => corroboratedIndices.has(allClaims.indexOf(c))).length;

  const visible = tab === "all" ? claims
    : tab === "draft" ? claims.filter(c => c.draft_approved)
    : tab === "dossier" ? claims.filter(c => (c.verification === "confirmed" || c.verification === "edited") && !c.draft_approved)
    : tab === "unsourced" ? claims.filter(c => !c.source_url)
    : tab === "corroborated" ? claims.filter(c => corroboratedIndices.has(allClaims.indexOf(c)))
    : claims.filter(c => c.verification === "unverified");

  const tabs: { id: FilterTab; label: string; count: number }[] = [
    { id: "all", label: "All", count: claims.length },
    { id: "review", label: "Needs review", count: needsReviewCount },
    { id: "draft", label: "In draft", count: draftCount },
    { id: "dossier", label: "Dossier only", count: dossierCount },
    ...(corroboratedCount > 0 ? [{ id: "corroborated" as FilterTab, label: "🌿 Corroborated", count: corroboratedCount }] : []),
    { id: "unsourced", label: "Unsourced", count: unsourcedCount },
  ];

  if (claims.length === 0) {
    return <p style={{ fontSize: 13, color: "var(--muted)", padding: "20px 0" }}>{emptyMessage}</p>;
  }

  async function doVerify(globalIndex: number, action: "confirm" | "edit" | "skip" | "approve_draft" | "remove_draft" | "edit_draft_text", text?: string) {
    setLoading(globalIndex);
    try {
      const resp = await verifyClaim(profileRef(profile), globalIndex, action, text);
      const updated = [...allClaims];
      updated[globalIndex] = resp.claim;
      onProfileUpdate({ ...profile, claims: updated });
    } catch { /* silently ignore */ }
    finally { setLoading(null); setEditingIndex(null); }
  }

  async function handleBatchAction(action: "approve_all_usable" | "confirm_all" | "skip_unverified") {
    setBatchLoading(action);
    try {
      const resp = await batchVerifyClaims(profileRef(profile), action);
      if (resp.profile) {
        onProfileUpdate(resp.profile);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setBatchLoading(null);
    }
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
          {draftCount} in draft · {dossierCount} in dossier · {needsReviewCount} pending
        </span>
      </div>

      {/* Batch actions bar when there are unreviewed claims */}
      {needsReviewCount > 0 && (
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
          background: "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)", border: "1px solid var(--border)",
          borderRadius: 8, padding: "8px 12px", marginBottom: 12, flexWrap: "wrap",
        }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>
            ⚡ Quick actions for {needsReviewCount} unreviewed claim{needsReviewCount === 1 ? "" : "s"}:
          </span>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button
              onClick={() => handleBatchAction("approve_all_usable")}
              disabled={Boolean(batchLoading)}
              className="btn-primary"
              style={{ fontSize: 11, padding: "4px 10px", minHeight: 0 }}
              title="Approve all claims from verified reliable sources directly into the draft"
            >
              {batchLoading === "approve_all_usable" ? "Approving…" : "+ Approve all usable for draft"}
            </button>
            <button
              onClick={() => handleBatchAction("confirm_all")}
              disabled={Boolean(batchLoading)}
              className="btn-ghost"
              style={{ fontSize: 11, padding: "4px 10px", minHeight: 0 }}
              title="Confirm all unreviewed claims into research dossier without including in draft"
            >
              {batchLoading === "confirm_all" ? "Confirming…" : "✓ Confirm all (dossier only)"}
            </button>
            <button
              onClick={() => handleBatchAction("skip_unverified")}
              disabled={Boolean(batchLoading)}
              className="btn-ghost"
              style={{ fontSize: 11, padding: "4px 10px", minHeight: 0, color: "var(--muted)" }}
              title="Skip remaining unreviewed claims"
            >
              {batchLoading === "skip_unverified" ? "Skipping…" : "✗ Skip unreviewed"}
            </button>
          </div>
        </div>
      )}

      {visible.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--muted)", padding: "16px 0" }}>
          {tab === "draft" ? "No claims included in the draft yet. Review claims and click '+' to include them." :
           tab === "dossier" ? "No claims in dossier-only mode. Confirmed claims not in the draft appear here." :
           tab === "unsourced" ? "No unsourced claims." :
           tab === "review" ? "All claims have been reviewed! Check 'In draft' or 'Dossier only'." : emptyMessage}
        </p>
      ) : (
        <div>
        {visible.map(claim => {
        const globalIndex = claimIndexMap.get(claim) ?? -1;
        const cluster = profile.saturation?.corroborated_clusters?.find(c => c.claim_indices.includes(globalIndex));
        const isEditing = editingIndex === globalIndex;
        const isLoading = loading === globalIndex;
        const src = claim.source_url ? profile.sources.find(s => s.url === claim.source_url) ?? null : null;
        // Mirror the draft audit's source rules so "+" is only enabled when the
        // claim can actually enter the draft.
        const sourceUsable = !!src && !!claim.source_url &&
          src.human_verified &&
          src.reliability !== "unreliable" &&
          src.relevance_flag !== "likely_wrong" &&
          !(src.liveness === "dead" && !src.archive_url);
        const includeBlocker = !claim.source_url
          ? "This claim has no source — add a source before including it in the draft."
          : !src
            ? "Source is not in this session."
            : !src.human_verified
              ? "Verify the source first — draft claims require a human-verified source."
              : src.reliability === "unreliable"
                ? "Source is marked unreliable."
                : src.relevance_flag === "likely_wrong"
                  ? "Source is flagged as a likely wrong person."
                  : src.liveness === "dead" && !src.archive_url
                    ? "Source is dead with no archive copy."
                    : "";
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
                  {claim.draft_approved ? (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "rgba(37, 99, 235, 0.12)", color: "var(--primary)" }}>
                      Included in draft
                    </span>
                  ) : (claim.verification === "confirmed" || claim.verification === "edited") ? (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "rgba(100, 116, 139, 0.12)", color: "#475569" }}>
                      Dossier only
                    </span>
                  ) : null}
                  {cluster && cluster.corroborating_sources.length > 1 && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "rgba(16, 185, 129, 0.12)", color: "var(--success)" }} title={`Corroborated across ${cluster.corroborating_sources.length} sources (${cluster.repetition_count} repeats)`}>
                      🌿 Corroborated ({cluster.corroborating_sources.length} sources)
                    </span>
                  )}
                  {claim.user_provided && (
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>· manual entry</span>
                  )}
                  {!claim.user_provided && claim.verification === "unverified" && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, background: "rgba(139, 92, 246, 0.12)", color: "#7c3aed" }}>
                      AI-suggested · review
                    </span>
                  )}
                </div>

                {isEditing ? (
                  <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
                    <div>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
                        {claim.draft_approved ? "Draft paraphrase (wikitext wording)" : "Claim fact text"}
                      </span>
                      <textarea
                        value={editText}
                        onChange={e => setEditText(e.target.value)}
                        style={{ width: "100%", height: 72, resize: "vertical", fontFamily: "inherit", fontSize: 13, marginTop: 3 }}
                        autoFocus
                      />
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                      <p style={{ fontSize: 13, lineHeight: 1.6, margin: 0 }}>{claim.text}</p>
                      {claim.date_context && (
                        <span style={{ fontSize: 11, color: "var(--muted)", fontStyle: "italic", whiteSpace: "nowrap" }}>
                          {claim.date_context}
                        </span>
                      )}
                    </div>
                    {claim.draft_text && claim.draft_text !== claim.text && (
                      <div style={{ marginTop: 5, padding: "5px 9px", background: "rgba(37, 99, 235, 0.07)", borderLeft: "3px solid var(--primary)", borderRadius: 4 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--primary)", display: "block" }}>
                          Custom draft wording:
                        </span>
                        <p style={{ fontSize: 12, margin: "2px 0 0", color: "var(--text)", lineHeight: 1.5 }}>{claim.draft_text}</p>
                      </div>
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
                      <a href={safeHref(claim.source_url)} target="_blank" rel="noreferrer"
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

              {/* Action buttons — for unverified/skipped */}
              {(claim.verification === "unverified" || claim.verification === "skipped") && !isEditing && (
                <div style={{ display: "flex", gap: 4, flexShrink: 0, alignItems: "center" }}>
                  <ActionBtn
                    onClick={() => doVerify(globalIndex, "approve_draft")}
                    disabled={isLoading || !sourceUsable}
                    color="var(--success)"
                    title={sourceUsable ? "Approve & include in draft" : includeBlocker}
                  >
                    + Draft
                  </ActionBtn>
                  <ActionBtn onClick={() => doVerify(globalIndex, "confirm")} disabled={isLoading} color="var(--primary)" title="Confirm for research dossier only">✓ Dossier</ActionBtn>
                  <ActionBtn onClick={() => { setEditingIndex(globalIndex); setEditText(claim.text); }} disabled={isLoading} color="var(--muted)" title="Edit">✎</ActionBtn>
                  <ActionBtn onClick={() => doVerify(globalIndex, "skip")} disabled={isLoading} color="var(--danger)" title="Skip">✗</ActionBtn>
                </div>
              )}
              {/* For confirmed/edited, allow toggling draft inclusion or editing */}
              {(claim.verification === "confirmed" || claim.verification === "edited") && !isEditing && (
                <div style={{ display: "flex", gap: 4, flexShrink: 0, alignItems: "center" }}>
                  <ActionBtn
                    onClick={() => {
                      setEditingIndex(globalIndex);
                      setEditText(claim.draft_text || claim.text);
                    }}
                    disabled={isLoading}
                    color="var(--primary)"
                    title={claim.draft_approved ? "Edit draft paraphrase wording" : "Edit claim text"}
                  >
                    ✎
                  </ActionBtn>
                  <ActionBtn
                    onClick={() => doVerify(globalIndex, claim.draft_approved ? "remove_draft" : "approve_draft")}
                    disabled={isLoading || (!claim.draft_approved && !sourceUsable)}
                    color={claim.draft_approved ? "var(--danger)" : "var(--success)"}
                    title={claim.draft_approved ? "Remove from draft (keep in dossier)" : (sourceUsable ? "Include in draft" : includeBlocker)}
                  >
                    {claim.draft_approved ? "− Draft" : "+ Draft"}
                  </ActionBtn>
                </div>
              )}
              {isEditing && (
                <div style={{ display: "flex", gap: 4, flexShrink: 0, alignItems: "center" }}>
                  <ActionBtn
                    onClick={() => doVerify(globalIndex, claim.draft_approved ? "edit_draft_text" : "edit", editText)}
                    disabled={isLoading}
                    color="var(--primary)"
                    title="Save edits"
                  >
                    ✓ Save
                  </ActionBtn>
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
    <button onClick={onClick} disabled={disabled} title={title} className="claim-action" style={{
      height: 28, padding: "0 8px", borderRadius: 6, background: "var(--bg)",
      border: "1px solid var(--border)", color, fontSize: 12, fontWeight: 700,
      display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 3,
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.45 : 1,
    }}>
      {children}
    </button>
  );
}

