import type { PersonProfile, DraftAudit } from "../types";

interface StageHeaderProps {
  profile: PersonProfile;
  audit: DraftAudit | null;
  auditError: string | null;
  onNavigate: (tab: "sources" | "profile" | "claims") => void;
}

interface StepItem {
  id: "identify" | "verify" | "review" | "draft";
  label: string;
  done: boolean;
  detail?: string;
}

function StepIndicator({ step, index, activeId }: { step: StepItem; index: number; activeId: string }) {
  const isDone = step.done;
  const isActive = step.id === activeId;
  return (
    <div style={{ display: "flex", alignItems: "center" }}>
      {index > 0 && <span style={{ width: 16, height: 1, background: "var(--border)", margin: "0 8px", flexShrink: 0 }} />}
      <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: isActive ? 800 : 600 }}>
        <span style={{
          width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          fontSize: 11, fontWeight: 800,
          background: isDone ? "var(--success)" : isActive ? "var(--primary)" : "var(--bg)",
          color: isDone || isActive ? "#fff" : "var(--muted)",
          border: isDone || isActive ? "none" : "1px solid var(--border)",
        }}>
          {isDone ? "✓" : index + 1}
        </span>
        <span style={{ color: isDone ? "var(--success)" : isActive ? "var(--primary)" : "var(--muted)" }}>
          {step.label}
          {step.detail && <span style={{ color: "var(--muted)", fontWeight: 500 }}> · {step.detail}</span>}
        </span>
      </span>
    </div>
  );
}

export function StageHeader({ profile, audit, auditError, onNavigate }: StageHeaderProps) {
  const totalSources = profile.sources.length;
  const verifiedCount = profile.sources.filter(s => s.human_verified).length;
  const unverifiedSources = totalSources - verifiedCount;
  const pendingClaims = profile.claims.filter(c => c.verification === "unverified").length;
  const inDraft = profile.claims.filter(c => c.draft_approved).length;
  const auditReady = audit?.ready === true;

  const steps: StepItem[] = [
    { id: "identify", label: "Identify", done: true },
    {
      id: "verify",
      label: "Verify",
      done: verifiedCount > 0 && unverifiedSources === 0,
      detail: totalSources ? `${verifiedCount}/${totalSources} verified` : undefined,
    },
    {
      id: "review",
      label: "Review",
      done: profile.claims.length > 0 && pendingClaims === 0 && inDraft > 0,
      detail: pendingClaims
        ? `${pendingClaims} to review`
        : inDraft
          ? `${inDraft} in draft`
          : profile.claims.length
            ? "dossier only"
            : undefined,
    },
    {
      id: "draft",
      label: "Draft",
      done: auditReady,
      detail: auditReady ? "ready" : audit ? "blocked" : undefined,
    },
  ];

  const activeId = steps.find(s => !s.done)?.id ?? "draft";

  return (
    <div className="card stage-header" style={{ marginBottom: 16, padding: "10px 16px", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", justifyContent: "space-between" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 0, flexWrap: "wrap" }}>
        {steps.map((step, i) => (
          <StepIndicator key={step.id} step={step} index={i} activeId={activeId} />
        ))}
      </div>
      <div className="stage-header-action" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {activeId === "draft" && !auditReady && auditError && (
          <span style={{ fontSize: 11, color: "var(--danger)" }}>{auditError}</span>
        )}
        {activeId === "verify" && unverifiedSources > 0 && (
          <button className="btn-primary" onClick={() => onNavigate("sources")} style={{ fontSize: 12, padding: "6px 14px" }}>
            Verify {unverifiedSources} source{unverifiedSources === 1 ? "" : "s"}
          </button>
        )}
        {activeId === "review" && pendingClaims > 0 && (
          <button className="btn-primary" onClick={() => onNavigate("claims")} style={{ fontSize: 12, padding: "6px 14px" }}>
            Review {pendingClaims} claim{pendingClaims === 1 ? "" : "s"}
          </button>
        )}
        {activeId === "review" && pendingClaims === 0 && inDraft === 0 && profile.claims.length > 0 && (
          <button className="btn-primary" onClick={() => onNavigate("claims")} style={{ fontSize: 12, padding: "6px 14px" }}>
            Select claims for draft
          </button>
        )}
      </div>
    </div>
  );
}

