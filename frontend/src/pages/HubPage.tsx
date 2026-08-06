import { useState, useEffect } from "react";
import type { PersonProfile, WikiStatus, DraftAudit } from "../types";
import { generateDraft, getDraftAudit, getSession, autoEnrich } from "../api";
import WorkspaceStatusBanner from "../components/WorkspaceStatusBanner";
import ResearchOperationsCard from "../components/ResearchOperationsCard";
import TimelineTab from "../components/TimelineTab";
import ClaimsReview from "../components/ClaimsReview";
import { SourcesPanel } from "../components/SourcesPanel";
import { ProfileTab } from "../components/ProfileTab";
import { TabBtn, NotabilityBadge, NotabilityCard, ChecklistCard, DraftReadinessCard } from "../components/WorkspaceCards";
import { getWorkspaceRoute } from "../workflow";


interface Props {
  initialProfile: PersonProfile;
  wikiStatus: WikiStatus;
  onDraft: (profile: PersonProfile) => void;
  onReset: () => void;
  relayPending?: { url: string; text: string } | null;
  onRelayConsumed?: () => void;
}

type Tab = "sources" | "profile" | "timeline" | "pending";

export default function HubPage({ initialProfile, wikiStatus, onDraft, onReset, relayPending, onRelayConsumed }: Props) {
  const [profile, setProfile] = useState(initialProfile);
  const [tab, setTab] = useState<Tab>("sources");
  const [drafting, setDrafting] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [activeOperations, setActiveOperations] = useState<Record<string, boolean>>({});
  const [draftError, setDraftError] = useState<string | null>(null);
  const [draftAudit, setDraftAudit] = useState<DraftAudit | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  // Track which source links the user has opened (session-local, not persisted)
  const [openedLinks, setOpenedLinks] = useState<Set<string>>(new Set());
  const [showBrowser, setShowBrowser] = useState(false);

  const hasVerifiedSources = profile.sources.some(s => s.human_verified);
  const workspaceRoute = getWorkspaceRoute(wikiStatus.status);
  const draftAvailable = workspaceRoute.draftLabel !== null && draftAudit?.ready === true;

  useEffect(() => {
    let cancelled = false;
    setAuditError(null);
    getDraftAudit(profile.name)
      .then(audit => { if (!cancelled) setDraftAudit(audit); })
      .catch(error => { if (!cancelled) setAuditError(String(error)); });
    return () => { cancelled = true; };
  }, [profile]);

  async function handleAutoEnrich() {
    setEnriching(true);
    try {
      const res = await autoEnrich(profile.name);
      if (res.ok) {
        const updated = await getSession(profile.name);
        setProfile(updated);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setEnriching(false);
    }
  }

  // Force sources tab if none verified
  useEffect(() => {
    if (!hasVerifiedSources) {
      setTab("sources");
    }
  }, [hasVerifiedSources]);

  // Switch to sources tab when Wiki+ relay content arrives
  useEffect(() => {
    if (relayPending) setTab("sources");
  }, [relayPending]);

  async function handleGenerateDraft() {
    setDrafting(true);
    setDraftError(null);
    try {
      const result = await generateDraft(profile.name);
      onDraft(result.profile);
    } catch (e) {
      setDraftError(String(e));
    } finally {
      setDrafting(false);
    }
  }

  function markLinkOpened(url: string) {
    setOpenedLinks(prev => new Set(prev).add(url));
  }

  const pendingClaims = profile.claims.filter(c => c.verification === "unverified");

  return (
    <div style={{ maxWidth: showBrowser ? 1500 : 1100, margin: "0 auto", padding: "20px 20px 60px", transition: "max-width 0.2s" }}>
      {/* Header */}
      <div className="workspace-header">
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {profile.photo_url ? (
            <img src={profile.photo_url} alt={profile.name}
              style={{ width: 52, height: 52, borderRadius: 8, objectFit: "cover", border: "1px solid var(--border)" }} />
          ) : (
            <div style={{
              width: 52, height: 52, borderRadius: 8, background: "var(--primary)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 22, fontWeight: 800, color: "#fff", flexShrink: 0,
            }}>
              {profile.name[0]}
            </div>
          )}
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 2 }}>{profile.name}</h1>
            <p style={{ fontSize: 13, color: "var(--muted)" }}>
              {[profile.field, profile.affiliation, profile.nationality].filter(Boolean).join(" · ")}
            </p>
            {hasVerifiedSources && profile.notability && <NotabilityBadge n={profile.notability} />}
          </div>
        </div>
        <div className="workspace-actions">
          <button className="btn-ghost" onClick={handleAutoEnrich} disabled={enriching} style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6, background: "linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)", border: "1px solid #7dd3fc" }}>
            {enriching ? "🔄 Auto-Enriching…" : "✨ Auto-Enrich Discovered Sources"}
          </button>
          <button className="btn-ghost" onClick={() => setShowBrowser(!showBrowser)} style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
            🖥️ {showBrowser ? "Hide Remote Browser" : "Show Remote Browser"}
          </button>
          <button className="btn-ghost" onClick={onReset} style={{ fontSize: 13 }}>New subject</button>
          {workspaceRoute.draftLabel && (
            <button className="btn-primary" onClick={handleGenerateDraft} disabled={drafting || !draftAvailable}>
              {drafting ? "Generating…" : workspaceRoute.draftLabel}
            </button>
          )}
        </div>
      </div>

      {draftError && (
        <div style={{ background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontSize: 13, color: "var(--danger)" }}>
          {draftError}
        </div>
      )}

      <WorkspaceStatusBanner wikiStatus={wikiStatus} />

      <div className="hub-grid" style={{ gridTemplateColumns: showBrowser ? "1fr 272px 420px" : "1fr 272px" }}>
        {/* Main panel */}
        <div>
          {/* Tabs */}
          {hasVerifiedSources ? (
            <div className="workspace-tabs">
              <TabBtn active={tab === "sources"} onClick={() => setTab("sources")}>
                Sources ({profile.sources.length})
              </TabBtn>
              <TabBtn active={tab === "profile"} onClick={() => setTab("profile")}>
                Subject Profile
                {(profile.missing_slots ?? []).length > 0 && (
                  <span style={{ marginLeft: 6, background: "var(--warning)", color: "#fff", borderRadius: 10, padding: "1px 7px", fontSize: 11 }}>
                    {(profile.missing_slots ?? []).length} missing
                  </span>
                )}
              </TabBtn>
              <TabBtn active={tab === "timeline"} onClick={() => setTab("timeline")}>
                Timeline
              </TabBtn>
              <TabBtn active={tab === "pending"} onClick={() => setTab("pending")}>
                Claims ({profile.claims.length})
                {pendingClaims.length > 0 && (
                  <span style={{ marginLeft: 6, background: "var(--primary)", color: "#fff", borderRadius: 10, padding: "1px 7px", fontSize: 11 }}>
                    {pendingClaims.length}
                  </span>
                )}
              </TabBtn>
            </div>
          ) : (
            <div className="card" style={{ padding: "18px 24px", marginBottom: 20, background: "linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%)", borderLeft: "4px solid var(--primary)", borderRadius: 12, boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)" }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 6px 0", color: "#1e3a8a", display: "flex", alignItems: "center", gap: 8 }}>
                🔍 Verify Discovered Sources
              </h2>
              <p style={{ fontSize: 13, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
                Wikimaker has fetched candidate sources for <strong>{profile.name}</strong>. Please confirm which sources actually correspond to your target person. Once confirmed, their facts will be automatically extracted to unlock the profile slots, timeline, and draft generator.
              </p>
            </div>
          )}

          {tab === "sources" && (
            <SourcesPanel
              profile={profile}
              openedLinks={openedLinks}
              onLinkOpen={markLinkOpened}
              onProfileUpdate={setProfile}
              relayPending={relayPending}
              onRelayConsumed={onRelayConsumed}
              onOperationStatusChange={(op, active) => {
                setActiveOperations(prev => ({ ...prev, [op]: active }));
              }}
              showBrowser={showBrowser}
              setShowBrowser={setShowBrowser}
            />
          )}
          {tab === "profile" && (
            <ProfileTab profile={profile} onProfileUpdate={setProfile} />
          )}
          {tab === "timeline" && (
            <TimelineTab profile={profile} onProfileUpdate={setProfile} />
          )}
          {tab === "pending" && (
            <ClaimsReview
              claims={profile.claims}
              allClaims={profile.claims}
              profile={profile}
              onProfileUpdate={setProfile}
              emptyMessage="No claims have been collected."
            />
          )}
        </div>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <ResearchOperationsCard ops={activeOperations} drafting={drafting} />
          {hasVerifiedSources ? (
            <>
              {profile.notability && <NotabilityCard n={profile.notability} />}
              <ChecklistCard profile={profile} wikiStatus={wikiStatus} />
              <DraftReadinessCard audit={draftAudit} error={auditError} />
              {workspaceRoute.draftLabel ? (
                <button className="btn-primary" onClick={handleGenerateDraft} disabled={drafting || !draftAvailable} style={{ width: "100%" }}>
                  {drafting ? "Generating…" : workspaceRoute.draftLabel}
                </button>
              ) : (
                <div className="card" style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>
                  Draft generation is unavailable in {workspaceRoute.label.toLowerCase()} mode. Continue researching and use verified findings to plan improvements.
                </div>
              )}
            </>
          ) : (
            <div className="card" style={{ padding: "24px 16px", textAlign: "center", color: "var(--muted)", borderRadius: 12, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 32, filter: "grayscale(10%)" }}>🛡️</span>
              <p style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text)" }}>Verify one source to continue</p>
              <p style={{ fontSize: 12, margin: 0, lineHeight: 1.5, color: "var(--muted)" }}>
                Confirm at least one source to extract facts and unlock the Subject Profile, Timeline, and available output tools.
              </p>
            </div>
          )}
        </div>

        {/* Companion Remote Browser */}
        {showBrowser && (
          <div className="card companion-browser">
            <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 13, fontWeight: 700 }}>Companion Remote Browser</span>
              <button onClick={() => setShowBrowser(false)} style={{ background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text)", cursor: "pointer", fontSize: 12, padding: "6px 12px" }}>
                Close ✕
              </button>
            </div>
            <iframe
              src="/browser/"
              style={{ width: "100%", flex: 1, border: "none" }}
              title="Companion Remote Browser"
            />
          </div>
        )}
      </div>
    </div>
  );
}
