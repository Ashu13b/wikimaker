import { useState } from "react";
import type { PersonProfile, WikiStatus, NotabilityResult, DraftAudit, ResearchSaturation } from "../types";

export function Expander({ label, open, onToggle, children }: {
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
  return <span style={{ fontSize: 12, color, fontWeight: 600, marginTop: 2, display: "inline-block" }}>{n.label} · {n.rs_count} significant source{n.rs_count !== 1 ? "s" : ""}</span>;
}

export function NotabilityCard({ n }: { n: NotabilityResult }) {
  const bg = n.score >= 0.7 ? "#dcfce7" : n.score >= 0.4 ? "#fef9c3" : "#fee2e2";
  const border = n.score >= 0.7 ? "#86efac" : n.score >= 0.4 ? "#fde047" : "#fca5a5";
  return (
    <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 8, padding: "12px 16px" }}>
      <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Notability: {n.label}</p>
      <p style={{ fontSize: 12 }}>{n.rs_count} significant editorial origin{n.rs_count !== 1 ? "s" : ""} · {n.candidate_count ?? 0} independent candidate{n.candidate_count !== 1 ? "s" : ""}</p>
      <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>{n.reason}</p>
    </div>
  );
}

export function SaturationCard({ s }: { s: ResearchSaturation }) {
  const [showClusters, setShowClusters] = useState(false);
  const isSaturated = s.level === "saturated";
  const isMature = s.level === "mature";
  const bg = isSaturated ? "#eff6ff" : isMature ? "#f0fdf4" : "#f8fafc";
  const border = isSaturated ? "#bfdbfe" : isMature ? "#bbf7d0" : "var(--border)";
  const levelColor = isSaturated ? "#2563eb" : isMature ? "#16a34a" : "#64748b";
  const pct = Math.round(s.score * 100);

  return (
    <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 8, padding: "14px 16px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6, flexWrap: "wrap", gap: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>
          Research Saturation: {pct}%
        </span>
        <span style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", padding: "2px 8px", borderRadius: 4, background: "#fff", color: levelColor, border: `1px solid ${border}` }}>
          {s.level === "saturated" ? "Saturated (Diminishing Returns)" : s.level === "mature" ? "Mature Coverage" : "Exploring"}
        </span>
      </div>

      <div style={{ width: "100%", height: 6, background: "rgba(0,0,0,0.06)", borderRadius: 3, overflow: "hidden", marginBottom: 10 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: levelColor, borderRadius: 3, transition: "width 0.3s" }} />
      </div>

      <p style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.5, margin: "0 0 10px" }}>
        {s.summary}
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, padding: "8px 0", borderTop: "1px solid rgba(0,0,0,0.06)", borderBottom: "1px solid rgba(0,0,0,0.06)", marginBottom: 8 }}>
        <div>
          <span style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", fontWeight: 700, display: "block" }}>Repeat Rate</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>{Math.round(s.repetition_rate * 100)}%</span>
        </div>
        <div>
          <span style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", fontWeight: 700, display: "block" }}>Fact Clusters</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>{s.unique_fact_count} / {s.total_claims_analyzed}</span>
        </div>
        <div>
          <span style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", fontWeight: 700, display: "block" }}>Syndicated Wires</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>{Math.round(s.syndication_rate * 100)}%</span>
        </div>
      </div>

      {s.corroborated_clusters.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <button
            onClick={() => setShowClusters(!showClusters)}
            style={{ background: "none", border: "none", padding: 0, fontSize: 11, fontWeight: 700, color: "var(--primary)", cursor: "pointer" }}
          >
            {showClusters ? "▴ Hide" : "▾ Show"} {s.corroborated_clusters.length} corroborated fact clusters
          </button>
          {showClusters && (
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
              {s.corroborated_clusters.slice(0, 5).map((cluster, idx) => (
                <div key={idx} style={{ padding: "6px 8px", background: "#fff", borderRadius: 6, border: "1px solid var(--border)", fontSize: 11 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                    <span style={{ fontWeight: 700, textTransform: "uppercase", color: "var(--muted)", fontSize: 10 }}>{cluster.field}</span>
                    <span style={{ fontWeight: 700, color: "var(--success)", fontSize: 10 }}>
                      🌿 {cluster.corroborating_sources.length} sources ({cluster.repetition_count} repeats)
                    </span>
                  </div>
                  <p style={{ margin: 0, color: "var(--text)", lineHeight: 1.4 }}>{cluster.canonical_text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function DraftReadinessCard({ audit, error }: { audit: DraftAudit | null; error: string | null }) {
  if (error) return <div className="card" style={{ color: "var(--danger)", fontSize: 12 }}>Evidence audit failed: {error}</div>;
  if (!audit) return <div className="card" style={{ color: "var(--muted)", fontSize: 12 }}>Auditing draft evidence…</div>;
  return (
    <div className="card" style={{ borderLeft: `4px solid ${audit.ready ? "var(--success)" : "var(--danger)"}` }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 6 }}>
        <p style={{ fontSize: 13, fontWeight: 700, margin: 0, color: audit.ready ? "var(--success)" : "var(--danger)" }}>
          {audit.ready ? "✓ Draft evidence sufficient" : "✕ Draft blocked"}
        </p>
        <span style={{ fontSize: 11, fontWeight: 700, padding: "1px 7px", borderRadius: 4, background: audit.ready ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.12)", color: audit.ready ? "var(--success)" : "var(--danger)" }}>
          {audit.ready ? "Ready" : "Action required"}
        </span>
      </div>
      <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 8px 0" }}>
        {audit.eligible_claim_count} eligible claims · {audit.eligible_source_count} cited sources · {audit.independent_source_count} independent outlets
      </p>

      {/* Blockers */}
      {audit.blockers.length > 0 && (
        <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, padding: "8px 10px", marginBottom: 8 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: "var(--danger)", margin: "0 0 4px 0", textTransform: "uppercase" }}>Blockers to resolve</p>
          {audit.blockers.map(b => (
            <p key={b.code} style={{ fontSize: 12, color: "#991b1b", margin: "2px 0", lineHeight: 1.4 }}>
              • {b.message}
            </p>
          ))}
        </div>
      )}

      {/* Warnings */}
      {audit.warnings.length > 0 && (
        <div style={{ marginBottom: 6 }}>
          {audit.warnings.map(w => (
            <p key={w.code} style={{ fontSize: 11, color: "var(--muted)", margin: "3px 0", lineHeight: 1.4 }}>
              ⚠️ {w.message} {w.count > 1 ? `(${w.count})` : ""}
            </p>
          ))}
        </div>
      )}

      {/* Exclusions expander */}
      {audit.exclusions && audit.exclusions.length > 0 && (
        <details style={{ marginTop: 8, borderTop: "1px solid var(--border)", paddingTop: 6 }}>
          <summary style={{ fontSize: 11, color: "var(--primary)", fontWeight: 600, cursor: "pointer" }}>
            {audit.excluded_claim_count} omitted claim reasons
          </summary>
          <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 3 }}>
            {audit.exclusions.map(ex => (
              <span key={ex.code} style={{ fontSize: 11, color: "var(--muted)" }}>
                • {ex.message}: {ex.count}
              </span>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

export function ChecklistCard({ profile, wikiStatus }: { profile: PersonProfile; wikiStatus: WikiStatus }) {
  const rsCount = profile.notability?.rs_count ?? 0;
  const verifiedCount = profile.claims.filter(c => c.verification === "confirmed" || c.verification === "edited").length;
  const humanVerifiedSources = profile.sources.filter(s => s.human_verified).length;
  const evidenceItems = [
    { done: rsCount >= 2, label: `2+ significant coverage origins (${rsCount} assessed)` },
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
    <button onClick={onClick} className={active ? "tab-btn tab-btn-active" : "tab-btn"} style={{
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
