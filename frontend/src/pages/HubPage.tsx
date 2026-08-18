import { useState, useEffect } from "react";
import type { PersonProfile, WikiStatus, DraftAudit } from "../types";
import { generateDraft, getDraftAudit, getSession, autoEnrich, profileRef } from "../api";
import WorkspaceStatusBanner from "../components/WorkspaceStatusBanner";
import ResearchOperationsCard from "../components/ResearchOperationsCard";
import ClaimsTab from "../components/ClaimsTab";
import ArticleProposalView from "../components/ArticleProposal";
import { SourcesPanel } from "../components/SourcesPanel";
import { ProfileTab } from "../components/ProfileTab";
import { StageHeader } from "../components/StageHeader";
import SummaryTab from "../components/SummaryTab";
import GuideTab from "../components/GuideTab";
import { TabBtn, NotabilityBadge, NotabilityCard, ChecklistCard, DraftReadinessCard } from "../components/WorkspaceCards";
import { getWorkspaceRoute } from "../workflow";


interface Props {
  initialProfile: PersonProfile;
  wikiStatus: WikiStatus;
  resumedSession?: boolean;
  onDraft: (profile: PersonProfile) => void;
  onReset: () => void;
  relayPending?: { url: string; text: string } | null;
  onRelayConsumed?: () => void;
}

type Tab = "summary" | "sources" | "profile" | "claims" | "proposal" | "guide";

export default function HubPage({ initialProfile, wikiStatus, resumedSession, onDraft, onReset, relayPending, onRelayConsumed }: Props) {
  const [profile, setProfile] = useState(initialProfile);
  const [showResumedBanner, setShowResumedBanner] = useState(Boolean(resumedSession));
  const [tab, setTab] = useState<Tab>("summary");
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

  // Why generation is (or isn't) possible — drives the disabled tooltip so it
  // is always clear when the draft can be generated.
  const draftBlocker = !workspaceRoute.draftLabel
    ? `Draft generation is unavailable in ${workspaceRoute.label.toLowerCase()} mode.`
    : !hasVerifiedSources
      ? "Verify at least one source before generating a draft."
      : !draftAudit
        ? "Auditing draft evidence…"
        : draftAudit.ready
          ? ""
          : `Evidence audit blocked: ${draftAudit.blockers[0]?.message ?? "review the audit warnings."}`;

  useEffect(() => {
    let cancelled = false;
    setAuditError(null);
    getDraftAudit(profileRef(profile))
      .then(audit => { if (!cancelled) setDraftAudit(audit); })
      .catch(error => { if (!cancelled) setAuditError(String(error)); });
    return () => { cancelled = true; };
  }, [profile]);

  async function handleAutoEnrich() {
    setEnriching(true);
    try {
      const res = await autoEnrich(profileRef(profile));
      if (res.ok) {
        const updated = await getSession(profileRef(profile));
        setProfile(updated);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setEnriching(false);
    }
  }

  // Force sources tab if none verified (summary/sources stay valid landing views)
  useEffect(() => {
    if (!hasVerifiedSources && (tab === "profile" || tab === "claims" || tab === "proposal")) {
      setTab("summary");
    }
  }, [hasVerifiedSources, tab]);

  // Switch to sources tab when Wiki+ relay content arrives
  useEffect(() => {
    if (relayPending) setTab("sources");
  }, [relayPending]);

  async function handleGenerateDraft() {
    setDrafting(true);
    setDraftError(null);
    try {
      const result = await generateDraft(profileRef(profile));
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
    <div className="hub-root" style={{ maxWidth: showBrowser ? 1500 : 1100, margin: "0 auto", padding: "20px 20px 60px", transition: "max-width 0.2s" }}>
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
            <button className="btn-primary" onClick={handleGenerateDraft} disabled={drafting || !draftAvailable}
              title={draftBlocker || undefined}>
              {drafting ? "Generating…" : workspaceRoute.draftLabel}
            </button>
          )}
        </div>
      </div>

      {showResumedBanner && (
        <div style={{ marginTop: 14, padding: "10px 14px", borderRadius: 8, background: "rgba(245, 158, 11, 0.12)", border: "1px solid #f59e0b55", color: "#92400e", fontSize: 13, display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ flex: 1 }}>A session for {profile.name} already existed — resumed it instead of starting over.</span>
          <button onClick={() => setShowResumedBanner(false)}
            style={{ background: "none", border: "none", color: "#92400e", fontSize: 15, cursor: "pointer", fontWeight: 700 }}>✕</button>
        </div>
      )}

      {draftError && (
        <div style={{ background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontSize: 13, color: "var(--danger)" }}>
          {draftError}
        </div>
      )}

      <WorkspaceStatusBanner wikiStatus={wikiStatus} />

      <StageHeader
        profile={profile}
        audit={draftAudit}
        auditError={auditError}
        onNavigate={setTab}
      />

      <div className="hub-grid" style={{ gridTemplateColumns: showBrowser
        ? (tab === "summary" || tab === "guide" ? "1fr 420px" : "1fr 272px 420px")
        : (tab === "summary" || tab === "guide" ? "1fr" : "1fr 272px") }}>
        {/* Main panel */}
        <div>
          {/* Tabs */}
          <div className="workspace-tabs">
            <TabBtn active={tab === "summary"} onClick={() => setTab("summary")}>
              Summary
            </TabBtn>
            <TabBtn active={tab === "sources"} onClick={() => setTab("sources")}>
              Sources ({profile.sources.length})
            </TabBtn>
            {hasVerifiedSources && (
              <>
                <TabBtn active={tab === "profile"} onClick={() => setTab("profile")}>
                  Subject Profile
                  {(profile.missing_slots ?? []).length > 0 && (
                    <span style={{ marginLeft: 6, background: "var(--warning)", color: "#fff", borderRadius: 10, padding: "1px 7px", fontSize: 11 }}>
                      {(profile.missing_slots ?? []).length} missing
                    </span>
                  )}
                </TabBtn>
                <TabBtn active={tab === "claims"} onClick={() => setTab("claims")}>
                  Claims ({profile.claims.length})
                  {pendingClaims.length > 0 && (
                    <span style={{ marginLeft: 6, background: "var(--primary)", color: "#fff", borderRadius: 10, padding: "1px 7px", fontSize: 11 }}>
                      {pendingClaims.length}
                    </span>
                  )}
                </TabBtn>
              </>
            )}
            {hasVerifiedSources && wikiStatus.status === "exists" && (
              <TabBtn active={tab === "proposal"} onClick={() => setTab("proposal")}>
                Article proposal
              </TabBtn>
            )}
            <TabBtn active={tab === "guide"} onClick={() => setTab("guide")}>
              📖 How It Works & Buttons
            </TabBtn>
          </div>
          <nav className="mobile-tabbar">
            <TabBtn active={tab === "summary"} onClick={() => setTab("summary")}>
              Summary
            </TabBtn>
            <TabBtn active={tab === "sources"} onClick={() => setTab("sources")}>
              Sources
            </TabBtn>
            {hasVerifiedSources && (
              <>
                <TabBtn active={tab === "profile"} onClick={() => setTab("profile")}>
                  Profile
                  {(profile.missing_slots ?? []).length > 0 && (
                    <span style={{ background: "var(--warning)", color: "#fff", borderRadius: 10, padding: "1px 6px", fontSize: 10 }}>
                      {(profile.missing_slots ?? []).length}
                    </span>
                  )}
                </TabBtn>
                <TabBtn active={tab === "claims"} onClick={() => setTab("claims")}>
                  Claims
                  {pendingClaims.length > 0 && (
                    <span style={{ background: "var(--primary)", color: "#fff", borderRadius: 10, padding: "1px 6px", fontSize: 10 }}>
                      {pendingClaims.length}
                    </span>
                  )}
                </TabBtn>
              </>
            )}
            {hasVerifiedSources && wikiStatus.status === "exists" && (
              <TabBtn active={tab === "proposal"} onClick={() => setTab("proposal")}>
                Proposal
              </TabBtn>
            )}
            <TabBtn active={tab === "guide"} onClick={() => setTab("guide")}>
              Guide
            </TabBtn>
          </nav>

          {tab === "summary" && (
            <SummaryTab
              profile={profile}
              wikiStatus={wikiStatus}
              audit={draftAudit}
              auditError={auditError}
              drafting={drafting}
              draftLabel={workspaceRoute.draftLabel}
              draftAvailable={draftAvailable}
              onNavigate={setTab}
              onGenerateDraft={handleGenerateDraft}
            />
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
          {tab === "claims" && (
            <ClaimsTab profile={profile} onProfileUpdate={setProfile} />
          )}
          {tab === "proposal" && wikiStatus.status === "exists" && (
            <ArticleProposalView profileName={profileRef(profile)} />
          )}
          {tab === "guide" && (
            <GuideTab />
          )}
        </div>

        {/* Sidebar */}
        {tab !== "summary" && tab !== "guide" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <ResearchOperationsCard ops={activeOperations} drafting={drafting} />
          {hasVerifiedSources ? (
            <>
              {profile.notability && <NotabilityCard n={profile.notability} />}
              <ChecklistCard profile={profile} wikiStatus={wikiStatus} />
              <DraftReadinessCard audit={draftAudit} error={auditError} />
              {!workspaceRoute.draftLabel && (
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
        )}

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
