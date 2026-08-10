import { useCallback, useEffect, useState } from "react";
import type { DraftLink, DraftLinkStatus } from "../types";
import { getDraftLinks } from "../api";
import { getHostname } from "../url";

const STATUS_META: Record<DraftLinkStatus, { label: string; bg: string; color: string }> = {
  ok: { label: "OK", bg: "#dcfce7", color: "#16a34a" },
  blocked: { label: "Blocked", bg: "#fef9c3", color: "#d97706" },
  dead: { label: "Dead", bg: "#fee2e2", color: "#dc2626" },
  unknown: { label: "Unknown", bg: "#f1f5f9", color: "#6b7280" },
};

export default function DraftLinks({ profileName }: { profileName: string }) {
  const [links, setLinks] = useState<DraftLink[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [manualVerified, setManualVerified] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setChecking(true);
    setError(null);
    try {
      setLinks(await getDraftLinks(profileName));
    } catch (e) {
      setError(String(e));
    } finally {
      setChecking(false);
    }
  }, [profileName]);

  useEffect(() => { load(); }, [load]);

  function toggleVerified(url: string) {
    setManualVerified(prev => {
      const next = new Set(prev);
      if (next.has(url)) next.delete(url); else next.add(url);
      return next;
    });
  }

  if (error) {
    return (
      <div className="card" style={{ fontSize: 13, color: "var(--danger)" }}>
        Could not load draft links: {error}
      </div>
    );
  }

  const counts: Record<DraftLinkStatus, number> = { ok: 0, blocked: 0, dead: 0, unknown: 0 };
  for (const link of links ?? []) counts[link.status]++;

  return (
    <div className="card" style={{ borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>
          External links in this draft
          {links && <span style={{ color: "var(--muted)", fontWeight: 400 }}> · {links.length} link{links.length === 1 ? "" : "s"}</span>}
        </p>
        <button className="btn-ghost" onClick={load} disabled={checking} style={{ fontSize: 12, padding: "6px 14px", minHeight: 0 }}>
          {checking ? "Checking…" : "Re-check links"}
        </button>
      </div>

      {links && (counts.blocked > 0 || counts.dead > 0) && (
        <div style={{ background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 8, padding: "10px 14px", fontSize: 12, marginBottom: 12, color: "#92400e" }}>
          {counts.dead} dead and {counts.blocked} blocked link{counts.blocked === 1 ? "" : "s"}. Open each below to confirm —
          dead pages should be replaced with an archived copy (archive-url) before submission.
        </div>
      )}

      {checking && links === null && (
        <p style={{ fontSize: 13, color: "var(--muted)", padding: "16px 0", textAlign: "center" }}>
          Checking each cited link…
        </p>
      )}

      {links && links.length === 0 && (
        <p style={{ fontSize: 13, color: "var(--muted)", padding: "16px 0" }}>
          No external links were found in the draft.
        </p>
      )}

      <div style={{ display: "flex", flexDirection: "column" }}>
        {links?.map(link => {
          const meta = STATUS_META[link.status];
          const verified = manualVerified.has(link.url);
          return (
            <div key={link.url} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 11, fontWeight: 700, borderRadius: 4, padding: "1px 8px", background: meta.bg, color: meta.color, flexShrink: 0, whiteSpace: "nowrap" }}>
                {meta.label}{link.status_code ? ` ${link.status_code}` : ""}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 600, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={link.label}>
                  {link.label || getHostname(link.url)}
                </p>
                <p style={{ fontSize: 11, color: "var(--muted)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {link.url}
                  {link.archived && <span style={{ marginLeft: 6, background: "rgba(99,102,241,0.12)", color: "#6366f1", borderRadius: 4, padding: "0 6px", fontWeight: 600 }}>archived</span>}
                </p>
              </div>
              <button
                onClick={() => toggleVerified(link.url)}
                title={verified ? "Marked as verified — click to unmark" : "I opened it and it's fine — mark verified"}
                style={{
                  width: 30, height: 30, flexShrink: 0, borderRadius: 6, border: "1px solid var(--border)",
                  background: verified ? "#dcfce7" : "var(--bg)", color: verified ? "#16a34a" : "var(--muted)",
                  fontSize: 14, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center",
                }}
              >
                ✓
              </button>
              <a href={link.url} target="_blank" rel="noreferrer" style={{ flexShrink: 0, fontSize: 12, color: "var(--primary)", fontWeight: 600 }}>
                Open ↗
              </a>
            </div>
          );
        })}
      </div>
    </div>
  );
}
