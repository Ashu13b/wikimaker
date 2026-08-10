import type { PersonProfile, DraftAudit } from "../types";

interface StageHeaderProps {
  profile: PersonProfile;
  audit: DraftAudit | null;
  auditError: string | null;
  onNavigate: (tab: "sources" | "profile" | "claims") => void;
}

export function StageHeader({ profile, audit, auditError, onNavigate }: StageHeaderProps) {
  const totalSources = profile.sources.length;
  const verifiedCount = profile.sources.filter(s => s.human_verified).length;
  const pendingClaims = profile.claims.filter(c => c.verification === "unverified").length;
  const confirmedNotApproved = profile.claims.filter(c => (c.verification === "confirmed" || c.verification === "edited") && !c.draft_approved).length;
  const awaitingReview = pendingClaims + confirmedNotApproved;
  const auditReady = audit?.ready === true;

  const steps: { id: "identify" | "verify" | "review" | "draft"; label: string; done: boolean; detail?: string }[] = [
    { id: "identify", label: "Identify", done: true },
    { id: "verify", label: "Verify", done: verifiedCount > 0, detail: totalSources ? `${verifiedCount}/${totalSources} verified` : undefined },
    { id: "review", label: "Review", done: profile.claims.length > 0 && awaitingReview === 0, detail: awaitingReview ? `${awaitingReview} claim${awaitingReview === 1 ? "" : "s"}` : profile.claims.length ? "all reviewed" : undefined },
    { id: "draft", label: "Draft", done: auditReady, detail: auditReady ? "ready" : audit ? "blocked" : undefined },
  ];

  const activeId = steps.find(s => !s.done)?.id ?? "draft";

  function action() {
    if (activeId === "verify") {
      const n = totalSources - verifiedCount;
      return (
        <button className="btn-primary" onClick={() => onNavigate("sources")} style={{ fontSize: 12, padding: "6px 14px" }}>
          Verify {n} source{n === 1 ? "" : "s"}
        </button>
      );
    }
    if (activeId === "review") {
      if (awaitingReview === 0) return null; // extraction hasn't produced claims yet
      return (
        <button className="btn-primary" onClick={() => onNavigate("claims")} style={{ fontSize: 12, padding: "6px 14px" }}>
          Review {awaitingReview} claim{awaitingReview === 1 ? "" : "s"}
        </button>
      );
    }
    return null; // the draft step is a status, not an action — the header holds the Generate button
  }

  return (
    <div className="card stage-header" style={{ marginBottom: 16, padding: "10px 16px", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", justifyContent: "space-between" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 0, flexWrap: "wrap" }}>
        {steps.map((step, i) => (
          <div key={step.id} style={{ display: "flex", alignItems: "center" }}>
            {i > 0 && <span style={{ width: 16, height: 1, background: "var(--border)", margin: "0 8px", flexShrink: 0 }} />}
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: step.id === activeId ? 800 : 600 }}>
              <span style={{
                width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontWeight: 800,
                background: step.done ? "var(--success)" : step.id === activeId ? "var(--primary)" : "var(--bg)",
                color: step.done || step.id === activeId ? "#fff" : "var(--muted)",
                border: step.done || step.id === activeId ? "none" : "1px solid var(--border)",
              }}>
                {step.done ? "✓" : i + 1}
              </span>
              <span style={{ color: step.done ? "var(--success)" : step.id === activeId ? "var(--primary)" : "var(--muted)" }}>
                {step.label}
                {step.detail && <span style={{ color: "var(--muted)", fontWeight: 500 }}> · {step.detail}</span>}
              </span>
            </span>
          </div>
        ))}
      </div>
      <div className="stage-header-action" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {activeId === "draft" && !auditReady && auditError && (
          <span style={{ fontSize: 11, color: "var(--danger)" }}>{auditError}</span>
        )}
        {action()}
      </div>
    </div>
  );
}
