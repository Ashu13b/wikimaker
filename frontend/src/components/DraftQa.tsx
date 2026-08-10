import { useCallback, useEffect, useState } from "react";
import type { DraftQaFinding, DraftQaReport } from "../types";
import { getDraftQa } from "../api";

const SEVERITY_META: Record<DraftQaFinding["severity"], { label: string; bg: string; color: string }> = {
  error: { label: "Error", bg: "#fee2e2", color: "#dc2626" },
  warning: { label: "Warning", bg: "#fef9c3", color: "#d97706" },
  info: { label: "Info", bg: "#f1f5f9", color: "#6b7280" },
};

export default function DraftQa({ profileName }: { profileName: string }) {
  const [report, setReport] = useState<DraftQaReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await getDraftQa(profileName));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [profileName]);

  useEffect(() => { load(); }, [load]);

  if (error) {
    return (
      <div className="card" style={{ fontSize: 13, color: "var(--danger)" }}>
        Could not run QA: {error}
      </div>
    );
  }

  return (
    <div className="card" style={{ borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>
          AfC review readiness
          {report && (
            <span style={{ color: report.passed ? "#16a34a" : "var(--muted)", fontWeight: 600, marginLeft: 8 }}>
              {report.passed ? "PASSES" : "NOT READY"}
            </span>
          )}
        </p>
        <button className="btn-ghost" onClick={load} disabled={loading} style={{ fontSize: 12, padding: "6px 14px", minHeight: 0 }}>
          {loading ? "Checking…" : "Re-run QA"}
        </button>
      </div>

      {report && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            {(["error", "warning", "info"] as const).map(sev => {
              const meta = SEVERITY_META[sev];
              return (
                <span key={sev} style={{ fontSize: 12, fontWeight: 600, background: meta.bg, color: meta.color, padding: "4px 10px", borderRadius: 999 }}>
                  {meta.label}: {report.counts[sev] ?? 0}
                </span>
              );
            })}
          </div>
          {report.findings.length === 0 && (
            <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>No findings — the draft looks structurally sound.</p>
          )}
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {report.findings.map((f, i) => {
              const meta = SEVERITY_META[f.severity];
              return (
                <li key={`${f.id}-${i}`} style={{ display: "flex", gap: 10, alignItems: "flex-start", fontSize: 13 }}>
                  <span style={{ flexShrink: 0, fontSize: 11, fontWeight: 700, background: meta.bg, color: meta.color, padding: "3px 8px", borderRadius: 999, textTransform: "uppercase", marginTop: 1 }}>
                    {meta.label}
                  </span>
                  <span style={{ lineHeight: 1.5 }}>{f.message}</span>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
