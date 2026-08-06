import type { PersonProfile, WikiStatus, NotabilityResult, DraftAudit } from "../types";
import { getWorkspaceRoute } from "../workflow";

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

export function NotabilityBadge({ n }: { n: NotabilityResult }) {
  const color = n.score >= 0.7 ? "var(--success)" : n.score >= 0.4 ? "var(--warning)" : "var(--danger)";
  return <span style={{ fontSize: 12, color, fontWeight: 600, marginTop: 2, display: "inline-block" }}>{n.label} · {n.rs_count} RS source{n.rs_count !== 1 ? "s" : ""}</span>;
}

export function NotabilityCard({ n }: { n: NotabilityResult }) {
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

export function DraftReadinessCard({ audit, error }: { audit: DraftAudit | null; error: string | null }) {
  if (error) return <div className="card" style={{ color: "var(--danger)", fontSize: 12 }}>Evidence audit failed: {error}</div>;
  if (!audit) return <div className="card" style={{ color: "var(--muted)", fontSize: 12 }}>Auditing draft evidence…</div>;
  const issues = audit.ready ? audit.warnings : audit.blockers;
  return (
    <div className="card" style={{ borderLeft: `4px solid ${audit.ready ? "var(--success)" : "var(--danger)"}` }}>
      <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>{audit.ready ? "Draft evidence sufficient" : "Draft blocked"}</p>
      <p style={{ fontSize: 12, color: "var(--muted)" }}>
        {audit.eligible_claim_count} eligible claims · {audit.eligible_source_count} cited sources · {audit.independent_source_count} independent outlets
      </p>
      {audit.ready && <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>This permits evidence-filtered drafting; it does not establish Wikipedia notability.</p>}
      {issues.map(issue => <p key={issue.code} style={{ fontSize: 12, marginTop: 6 }}>{issue.message} ({issue.count})</p>)}
      {audit.excluded_claim_count > 0 && <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>{audit.excluded_claim_count} unsafe or unusable claims will be omitted.</p>}
    </div>
  );
}

export function ChecklistCard({ profile, wikiStatus }: { profile: PersonProfile; wikiStatus: WikiStatus }) {
  const rsCount = profile.notability?.rs_count ?? 0;
  const verifiedCount = profile.claims.filter(c => c.verification === "confirmed" || c.verification === "edited").length;
  const humanVerifiedSources = profile.sources.filter(s => s.human_verified).length;
  const evidenceItems = [
    { done: rsCount >= 2, label: `2+ RS sources (${rsCount} found)` },
    { done: humanVerifiedSources > 0, label: `Sources checked (${humanVerifiedSources}/${profile.sources.length})` },
    { done: verifiedCount > 0, label: `Claims verified (${verifiedCount}/${profile.claims.length})` },
  ];
  const statusItem = wikiStatus.status === "clear"
    ? { done: true, label: "No existing article or draft found" }
    : wikiStatus.status === "draft"
      ? { done: true, label: "Existing draft identified" }
      : wikiStatus.status === "exists"
        ? { done: true, label: "Existing article identified" }
        : { done: false, label: "Prior deletion requires review" };
  const items = [...evidenceItems, statusItem];
  return (
    <div className="card">
      <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>
        {wikiStatus.status === "clear" || wikiStatus.status === "draft" ? "Draft readiness" : "Research readiness"}
      </p>
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

export function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
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
