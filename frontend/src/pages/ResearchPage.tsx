import { useEffect, useState } from "react";
import { startResearch } from "../api";
import type { PersonCandidate, PersonProfile, WikiStatus } from "../types";

interface Props {
  candidate: PersonCandidate;
  onDone: (profile: PersonProfile, wikiStatus: WikiStatus) => void;
  onBack: () => void;
}

const STEPS = [
  "Checking Wikipedia for existing pages...",
  "Fetching sources from Semantic Scholar and web...",
  "Classifying source reliability...",
  "Scoring notability against WP:GNG...",
  "Extracting claims with citations...",
  "Building research workspace...",
];

export default function ResearchPage({ candidate, onDone, onBack }: Props) {
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    const interval = setInterval(() => {
      setStepIndex(i => Math.min(i + 1, STEPS.length - 1));
    }, 2500);

    startResearch(candidate)
      .then(result => {
        if (!alive) return;
        clearInterval(interval);
        onDone(result.profile, result.wiki_status);
      })
      .catch(e => {
        if (!alive) return;
        clearInterval(interval);
        setError(String(e));
      });

    return () => { alive = false; clearInterval(interval); };
  }, []);

  return (
    <div style={{ maxWidth: 520, margin: "80px auto", padding: "0 20px", textAlign: "center" }}>
      <div className="card">
        <div style={{
          width: 56, height: 56, borderRadius: "50%",
          background: "var(--primary)", margin: "0 auto 20px",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          {error
            ? <span style={{ color: "#fff", fontSize: 24 }}>!</span>
            : <Spinner />
          }
        </div>

        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
          Researching {candidate.name}
        </h2>

        {error ? (
          <>
            <p style={{ color: "var(--danger)", fontSize: 14, marginBottom: 20 }}>{error}</p>
            <button className="btn-ghost" onClick={onBack}>Go back</button>
          </>
        ) : (
          <>
            <p style={{ color: "var(--muted)", fontSize: 14, marginBottom: 24 }}>
              {STEPS[stepIndex]}
            </p>
            <div style={{
              height: 4, background: "var(--bg)", borderRadius: 2, overflow: "hidden",
            }}>
              <div style={{
                height: "100%",
                width: `${((stepIndex + 1) / STEPS.length) * 100}%`,
                background: "var(--primary)",
                transition: "width 0.5s ease",
              }} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
      <style>{`@keyframes spin{to{transform:rotate(360deg)}} .s{animation:spin 0.8s linear infinite;transform-origin:center}`}</style>
      <circle className="s" cx="12" cy="12" r="9" strokeDasharray="40 16" />
    </svg>
  );
}
