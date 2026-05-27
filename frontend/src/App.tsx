import { useState, useEffect } from "react";
import IdentifyPage from "./pages/IdentifyPage";
import ResearchPage from "./pages/ResearchPage";
import HubPage from "./pages/HubPage";
import DraftPage from "./pages/DraftPage";
import type { PersonCandidate, PersonProfile, WikiStatus } from "./types";

type Stage = "identify" | "loading" | "hub" | "draft";

export default function App() {
  const [stage, setStage] = useState<Stage>("identify");
  const [confirmed, setConfirmed] = useState<PersonCandidate | null>(null);
  const [hubProfile, setHubProfile] = useState<PersonProfile | null>(null);
  const [wikiStatus, setWikiStatus] = useState<WikiStatus | null>(null);
  const [draftProfile, setDraftProfile] = useState<PersonProfile | null>(null);
  const [generateHindi, setGenerateHindi] = useState(false);
  const [relayPending, setRelayPending] = useState<{ url: string; text: string } | null>(null);

  // Pick up Wiki+ relay from browser_server: ?relay_url=&relay_text=
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const relay_url = params.get("relay_url");
    const relay_text = params.get("relay_text");
    if (relay_url && relay_text) {
      setRelayPending({ url: relay_url, text: relay_text });
      // Clean URL without reload
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  function handleConfirmed(candidate: PersonCandidate) {
    setConfirmed(candidate);
    setStage("loading");
  }

  function handleResearchDone(profile: PersonProfile, status: WikiStatus) {
    setHubProfile(profile);
    setWikiStatus(status);
    setStage("hub");
  }

  function handleDraft(profile: PersonProfile) {
    setDraftProfile(profile);
    setStage("draft");
  }

  function handleReset() {
    setStage("identify");
    setConfirmed(null);
    setHubProfile(null);
    setWikiStatus(null);
    setDraftProfile(null);
  }

  const hindiToggle = stage === "identify" ? (
    <div style={{ position: "fixed", top: 16, right: 20, fontSize: 13 }}>
      <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
        <input
          type="checkbox"
          checked={generateHindi}
          onChange={e => setGenerateHindi(e.target.checked)}
          style={{ width: "auto" }}
        />
        Hindi draft
      </label>
    </div>
  ) : null;

  return (
    <>
      {hindiToggle}
      {stage === "identify" && (
        <IdentifyPage
          onConfirmed={handleConfirmed}
          onResume={(profile, status) => {
            setHubProfile(profile);
            setWikiStatus(status);
            setStage("hub");
          }}
        />
      )}
      {stage === "loading" && confirmed && (
        <ResearchPage
          candidate={confirmed}
          onDone={handleResearchDone}
          onBack={() => setStage("identify")}
        />
      )}
      {stage === "hub" && hubProfile && wikiStatus && (
        <HubPage
          initialProfile={hubProfile}
          wikiStatus={wikiStatus}
          generateHindi={generateHindi}
          onDraft={handleDraft}
          onReset={handleReset}
          relayPending={relayPending}
          onRelayConsumed={() => setRelayPending(null)}
        />
      )}
      {stage === "draft" && draftProfile && wikiStatus && (
        <DraftPage
          profile={draftProfile}
          wikiStatus={wikiStatus}
          onBackToHub={() => setStage("hub")}
          onReset={handleReset}
        />
      )}
    </>
  );
}
