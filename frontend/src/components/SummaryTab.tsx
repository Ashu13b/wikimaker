import type { PersonProfile, WikiStatus, DraftAudit } from "../types";
import { NotabilityCard, ChecklistCard, DraftReadinessCard, SaturationCard } from "./WorkspaceCards";

type Tab = "sources" | "profile" | "claims" | "proposal" | "guide";

interface Props {
  profile: PersonProfile;
  wikiStatus: WikiStatus;
  audit: DraftAudit | null;
  auditError: string | null;
  drafting: boolean;
  draftLabel: string | null;
  draftAvailable: boolean;
  onNavigate: (tab: Tab) => void;
  onGenerateDraft: () => void;
}

export default function SummaryTab({ profile, wikiStatus, audit, auditError, drafting, draftLabel, draftAvailable, onNavigate, onGenerateDraft }: Props) {
  const totalSources = profile.sources.length;
  const verifiedCount = profile.sources.filter(s => s.human_verified).length;
  const unverifiedCount = totalSources - verifiedCount;
  const pendingClaims = profile.claims.filter(c => c.verification === "unverified").length;
  const inDraft = profile.claims.filter(c => c.draft_approved).length;
  const auditReady = audit?.ready === true;
  const rsCount = profile.notability?.rs_count ?? 0;

  const milestones: { id: "verify" | "review" | "draft"; label: string; done: boolean; detail: string; tab: Tab }[] = [
    {
      id: "verify", label: "Verify sources", done: verifiedCount > 0 && unverifiedCount === 0,
      detail: `${verifiedCount}/${totalSources} confirmed`,
      tab: "sources",
    },
    {
      id: "review", label: "Review claims", done: profile.claims.length > 0 && pendingClaims === 0 && inDraft > 0,
      detail: pendingClaims
        ? `${pendingClaims} to review`
        : inDraft
          ? `${inDraft} in draft`
          : profile.claims.length
            ? "dossier only"
            : "no claims yet",
      tab: "claims",
    },
    {
      id: "draft", label: "Generate draft", done: auditReady,
      detail: auditReady ? "ready" : audit ? "blocked" : "waiting",
      tab: "claims",
    },
  ];

  const next: { title: string; detail: string; tab: Tab | null; generate: boolean } = (() => {
    if (verifiedCount === 0) return {
      title: unverifiedCount ? `Verify ${unverifiedCount} source${unverifiedCount === 1 ? "" : "s"}` : "Add your first source",
      detail: unverifiedCount
        ? "Confirm which fetched sources really describe this person — verified sources unlock claim extraction."
        : "Use the research tools to find sources about this person — verified sources unlock claim extraction.",
      tab: "sources",
      generate: false,
    };
    if (pendingClaims > 0) return {
      title: `Review ${pendingClaims} claim${pendingClaims === 1 ? "" : "s"}`,
      detail: "Review AI-suggested claims — include verified facts in the draft or keep them in the research dossier.",
      tab: "claims",
      generate: false,
    };
    if (inDraft === 0 && profile.claims.length > 0) return {
      title: "Select claims for draft",
      detail: "You have confirmed claims in your research dossier, but none selected for drafting. Include key claims to build the draft.",
      tab: "claims",
      generate: false,
    };
    if (draftLabel && auditReady) return {
      title: draftLabel.replace("→", "").trim(),
      detail: `Evidence is sufficient (${inDraft} claim${inDraft === 1 ? "" : "s"} across ${audit?.eligible_source_count ?? 0} sources) — generate the wikitext draft.`,
      tab: null,
      generate: true,
    };
    return {
      title: "Keep researching",
      detail: auditError ?? (audit
        ? (audit.blockers[0]?.message ?? "The draft audit needs a few more independent sources before it can proceed.")
        : "Auditing draft evidence…"),
      tab: "sources",
      generate: false,
    };
  })();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Next action */}
      <div className="card" style={{ borderLeft: `4px solid var(--${next.generate ? "success" : "primary"})`, background: "linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%)" }}>
        <p style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1, color: "var(--muted)", margin: "0 0 4px" }}>
          Next step
        </p>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <p style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>{next.title}</p>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: "4px 0 0", maxWidth: 560, lineHeight: 1.5 }}>{next.detail}</p>
          </div>
          {next.generate
            ? <button className="btn-primary" onClick={onGenerateDraft} disabled={drafting || !draftAvailable}>{drafting ? "Generating…" : draftLabel}</button>
            : <button className="btn-primary" onClick={() => onNavigate(next.tab!)}>Go</button>}
        </div>
      </div>

      {/* Stat tiles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <StatTile label="Sources" value={`${verifiedCount}/${totalSources}`} sub="verified" tone={verifiedCount > 0 ? "success" : "muted"} />
        <StatTile label="Claims" value={`${profile.claims.length}`} sub={`${inDraft} in draft`} tone={inDraft > 0 ? "success" : "muted"} />
        <StatTile label="Significant coverage" value={`${rsCount}`} sub={`${profile.notability?.candidate_count ?? 0} independent candidates`} tone={rsCount >= 2 ? "success" : "muted"} />
        <StatTile label="Draft" value={auditReady ? "Ready" : "Waiting"} sub={audit ? (auditReady ? "evidence ok" : "blocked") : "auditing…"} tone={auditReady ? "success" : "muted"} />
      </div>

      <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Research dossier</p>
          <p style={{ fontSize: 12, color: "var(--muted)", margin: "4px 0 0" }}>Export all retained evidence, notes, research-only claims, and draft-selected claims.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-ghost" onClick={() => void navigator.clipboard.writeText(buildResearchDossier(profile))}>Copy Markdown</button>
          <button className="btn-ghost" onClick={() => downloadResearchDossier(profile)}>Download</button>
        </div>
      </div>

      {/* Milestones */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Progress</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {milestones.map(m => (
            <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
              <span style={{
                width: 22, height: 22, borderRadius: "50%", flexShrink: 0,
                display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 12,
                background: m.done ? "var(--success)" : "var(--bg)",
                color: m.done ? "#fff" : "var(--muted)",
                border: m.done ? "none" : "1px solid var(--border)",
              }}>
                {m.done ? "✓" : "·"}
              </span>
              <span style={{ fontWeight: 700, flex: 1 }}>{m.label}</span>
              <span style={{ color: "var(--muted)", fontSize: 12 }}>{m.detail}</span>
              {!m.done && <button className="btn-ghost" onClick={() => onNavigate(m.tab)} style={{ fontSize: 11, padding: "4px 12px", minHeight: 0 }}>Go</button>}
            </div>
          ))}
        </div>
      </div>

      {/* Quick Guide Callout Banner */}
      <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14, background: "rgba(37, 99, 235, 0.04)", border: "1px solid rgba(37, 99, 235, 0.18)", padding: "14px 18px", flexWrap: "wrap" }}>
        <div>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--primary)", display: "block" }}>
            📖 How Wikimaker Works & Button Guide
          </span>
          <p style={{ fontSize: 12, color: "var(--muted)", margin: "2px 0 0" }}>
            Confused about what "+ Draft", "✓ Dossier", or "Verify Source" do? Read the interactive visual guide.
          </p>
        </div>
        <button className="btn-ghost" onClick={() => onNavigate("guide")} style={{ fontSize: 12, padding: "6px 14px", fontWeight: 700 }}>
          Open Guide →
        </button>
      </div>

      {/* Status cards */}
      {profile.saturation && <SaturationCard s={profile.saturation} />}
      {verifiedCount > 0 && profile.notability && <NotabilityCard n={profile.notability} />}
      {verifiedCount > 0 && <ChecklistCard profile={profile} wikiStatus={wikiStatus} />}
      {verifiedCount > 0 && <DraftReadinessCard audit={audit} error={auditError} />}
    </div>
  );
}
function buildResearchDossier(profile: PersonProfile): string {
  const sourcesByUrl = new Map(profile.sources.map(source => [source.url, source]));
  const claimLine = (claim: PersonProfile["claims"][number]) => {
    const source = claim.source_url ? sourcesByUrl.get(claim.source_url) : null;
    const citation = source ? ` — [${source.publisher || source.title}](${source.url})` : " — no public source";
    return `- **${claim.field}**: ${claim.draft_text || claim.text}${citation}`;
  };
  const section = (title: string, claims: PersonProfile["claims"]) => [
    `## ${title}`, claims.length ? claims.map(claimLine).join("\n") : "_None._", "",
  ];
  const draftClaims = profile.claims.filter(claim => claim.draft_approved);
  const researchOnly = profile.claims.filter(claim =>
    !claim.draft_approved && (claim.verification === "confirmed" || claim.verification === "edited"));
  const leads = profile.claims.filter(claim => claim.verification === "unverified");
  const sourceLines = profile.sources.map(source => {
    const assessment = source.coverage_depth === "significant" ? "significant coverage"
      : source.coverage_depth === "passing_mention" ? "passing mention" : "not assessed";
    const origin = source.editorial_origin ? `; origin: ${source.editorial_origin}` : "";
    const notes = source.research_notes ? ` — ${source.research_notes}` : "";
    return `- [${source.title || source.url}](${source.url}) — ${source.publisher}; ${assessment}${origin}${notes}`;
  });
  return [
    `# Research dossier: ${profile.name}`, "",
    `Generated from the saved Wikimaker session. ${profile.sources.length} sources; ${profile.claims.length} claims; ${draftClaims.length} selected for drafting.`, "",
    ...section("Draft-selected evidence", draftClaims),
    ...section("Confirmed research-only evidence", researchOnly),
    ...section("Unverified leads", leads),
    "## Source inventory", sourceLines.length ? sourceLines.join("\n") : "_None._", "",
  ].join("\n");
}

function downloadResearchDossier(profile: PersonProfile) {
  const blob = new Blob([buildResearchDossier(profile)], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${profile.name.replace(/[^a-z0-9]+/gi, "_")}_research_dossier.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function StatTile({ label, value, sub, tone }: { label: string; value: string; sub: string; tone: "success" | "muted" }) {
  const color = tone === "success" ? "var(--success)" : "var(--muted)";
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--muted)", margin: 0 }}>{label}</p>
      <p style={{ fontSize: 24, fontWeight: 800, margin: "4px 0 0", color }}>{value}</p>
      <p style={{ fontSize: 11, color: "var(--muted)", margin: 0 }}>{sub}</p>
    </div>
  );
}
