import { useState } from "react";
import type { PersonProfile, WikiStatus, Source } from "../types";

interface Props {
  profile: PersonProfile;
  wikiStatus: WikiStatus;
  onBackToHub: () => void;
  onReset: () => void;
}

export default function DraftPage({ profile, wikiStatus, onBackToHub, onReset }: Props) {
  const [tab, setTab] = useState<"en" | "hi">("en");
  const [copied, setCopied] = useState(false);

  const wikitextEn = profile.wikitext_en ?? "";
  const wikitextHi = profile.wikitext_hi ?? "";
  const current = tab === "en" ? wikitextEn : wikitextHi;

  function handleCopy() {
    // navigator.clipboard is browser-only — kept in component, not api.ts
    if (navigator.clipboard) {
      navigator.clipboard.writeText(current).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }

  const notability = profile.notability;
  const rsCount = notability?.rs_count ?? 0;

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", padding: "0 20px 60px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {profile.photo_url && (
            <img src={profile.photo_url} alt={profile.name}
              style={{ width: 48, height: 48, borderRadius: 8, objectFit: "cover", border: "1px solid var(--border)" }} />
          )}
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 2 }}>{profile.name}</h1>
            <p style={{ fontSize: 13, color: "var(--muted)" }}>
              {[profile.field, profile.affiliation].filter(Boolean).join(" · ")}
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-ghost" onClick={onBackToHub} style={{ fontSize: 13 }}>
            ← Back to research
          </button>
          <button className="btn-ghost" onClick={onReset} style={{ fontSize: 13 }}>New search</button>
        </div>
      </div>

      {/* Notability — informational only, never a gate */}
      {notability && (
        <div style={{
          background: rsCount >= 2 ? "#dcfce7" : "#fef9c3",
          border: `1px solid ${rsCount >= 2 ? "#86efac" : "#fde047"}`,
          borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontSize: 13,
        }}>
          <strong>Notability: {notability.label}</strong> — {rsCount} reliable secondary source{rsCount !== 1 ? "s" : ""} · {notability.reason}
        </div>
      )}

      {(wikiStatus.status === "deleted" || wikiStatus.status === "draft") && wikiStatus.note && (
        <div style={{
          background: "#fef9c3", border: "1px solid #fde047",
          borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontSize: 13,
        }}>
          <strong>Note:</strong> {wikiStatus.note}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 272px", gap: 20, alignItems: "start" }}>
        {/* Draft */}
        <div className="card" style={{ padding: 0 }}>
          <div style={{ display: "flex", borderBottom: "1px solid var(--border)" }}>
            <TabBtn active={tab === "en"} onClick={() => setTab("en")}>English draft</TabBtn>
            {wikitextHi && <TabBtn active={tab === "hi"} onClick={() => setTab("hi")}>Hindi draft</TabBtn>}
          </div>
          <div style={{ padding: 20 }}>
            <textarea
              readOnly
              value={current}
              style={{
                width: "100%", height: 520, fontFamily: "monospace", fontSize: 12,
                border: "none", resize: "vertical", outline: "none", lineHeight: 1.6,
              }}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="btn-primary" onClick={handleCopy}>
                {copied ? "Copied!" : "Copy wikitext"}
              </button>
              <a
                href="https://en.wikipedia.org/wiki/Wikipedia:Articles_for_creation/submissions"
                target="_blank" rel="noreferrer"
                style={{ display: "inline-flex", alignItems: "center" }}
              >
                <button className="btn-ghost">Submit to AfC →</button>
              </a>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card">
            <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>AfC checklist</p>
            {[
              { done: rsCount >= 2, label: `2+ RS sources (${rsCount})` },
              { done: !!wikitextEn, label: "Draft generated" },
              { done: profile.claims.some(c => c.verification === "confirmed" || c.verification === "edited"), label: "At least one claim verified" },
              { done: wikiStatus.status !== "exists", label: "No existing article" },
              { done: wikiStatus.status !== "deleted", label: "No prior deletion" },
            ].map((item, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7, fontSize: 12 }}>
                <span style={{ color: item.done ? "var(--success)" : "var(--muted)", fontWeight: 700 }}>
                  {item.done ? "✓" : "·"}
                </span>
                <span style={{ color: item.done ? "var(--text)" : "var(--muted)" }}>{item.label}</span>
              </div>
            ))}
          </div>

          <div className="card">
            <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>
              Sources ({profile.sources.length})
            </p>
            {profile.sources.map((s, i) => <SourceRow key={i} source={s} />)}
          </div>
        </div>
      </div>
    </div>
  );
}

function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "12px 20px", border: "none", borderRadius: 0, background: "transparent",
        fontWeight: active ? 700 : 400,
        borderBottom: active ? "2px solid var(--primary)" : "2px solid transparent",
        color: active ? "var(--primary)" : "var(--muted)",
        fontSize: 13, cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

function SourceRow({ source }: { source: Source }) {
  const tagClass: Record<string, string> = {
    reliable_secondary: "tag-rs",
    primary: "tag-primary",
    self_published: "tag-self",
    unreliable: "tag-unreliable",
  };
  const tagLabel: Record<string, string> = {
    reliable_secondary: "RS",
    primary: "Primary",
    self_published: "Self",
    unreliable: "Unreliable",
  };
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
        <span className={`tag ${tagClass[source.reliability]}`}>{tagLabel[source.reliability]}</span>
        <a href={source.url} target="_blank" rel="noreferrer"
          style={{ fontSize: 12, color: "var(--primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {source.publisher || new URL(source.url).hostname}
        </a>
      </div>
      <p style={{ fontSize: 12, color: "var(--muted)" }} title={source.title}>
        {source.title.slice(0, 64)}{source.title.length > 64 ? "…" : ""}
      </p>
    </div>
  );
}
