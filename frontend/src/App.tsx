import { useState, useEffect, Component, ReactNode, ErrorInfo } from "react";
import IdentifyPage from "./pages/IdentifyPage";
import ResearchPage from "./pages/ResearchPage";
import HubPage from "./pages/HubPage";
import DraftPage from "./pages/DraftPage";
import type { PersonCandidate, PersonProfile, WikiStatus } from "./types";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Wikimaker UI Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ maxWidth: 600, margin: "60px auto", padding: 24, background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 12 }}>
          <h2 style={{ fontSize: 18, color: "#991b1b", marginBottom: 8 }}>Something went wrong in the workspace</h2>
          <p style={{ fontSize: 13, color: "#7f1d1d", marginBottom: 16, fontFamily: "monospace", wordBreak: "break-all" }}>
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => window.location.reload()}
              style={{ padding: "8px 16px", borderRadius: 6, border: "none", background: "#b91c1c", color: "#fff", cursor: "pointer", fontWeight: 700 }}
            >
              Reload Page
            </button>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", background: "#fff", color: "#333", cursor: "pointer" }}
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

type Stage = "identify" | "loading" | "hub" | "draft";

function MainApp() {
  const [stage, setStage] = useState<Stage>("identify");
  const [confirmed, setConfirmed] = useState<PersonCandidate | null>(null);
  const [hubProfile, setHubProfile] = useState<PersonProfile | null>(null);
  const [wikiStatus, setWikiStatus] = useState<WikiStatus | null>(null);
  const [resumedSession, setResumedSession] = useState(false);
  const [draftProfile, setDraftProfile] = useState<PersonProfile | null>(null);
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

  // Listen for WIKIMAKER_RELAY messages from the embedded browser iframe
  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (event.data && event.data.type === "WIKIMAKER_RELAY") {
        setRelayPending({ url: event.data.url, text: event.data.text });
      }
    }
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  function handleConfirmed(candidate: PersonCandidate) {
    setConfirmed(candidate);
    setStage("loading");
  }

  function handleResearchDone(profile: PersonProfile, status: WikiStatus, resumed?: boolean) {
    setHubProfile(profile);
    setWikiStatus(status);
    setResumedSession(Boolean(resumed));
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
    setResumedSession(false);
    setDraftProfile(null);
  }

  return (
    <>
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
          resumedSession={resumedSession}
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

export default function App() {
  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  );
}
