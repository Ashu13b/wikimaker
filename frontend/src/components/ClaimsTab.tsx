import { useState } from "react";
import type { PersonProfile } from "../types";
import ClaimsReview from "./ClaimsReview";
import TimelineTab from "./TimelineTab";

type Mode = "review" | "timeline";

export default function ClaimsTab({ profile, onProfileUpdate, onLoadSuggestions }: {
  profile: PersonProfile;
  onProfileUpdate: (p: PersonProfile) => void;
  onLoadSuggestions?: () => void;
}) {
  const [mode, setMode] = useState<Mode>("review");
  const pendingCount = profile.claims.filter(c => c.verification === "unverified").length;
  const draftCount = profile.claims.filter(c => c.draft_approved).length;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "14px 0 4px", flexWrap: "wrap" }}>
        {(["review", "timeline"] as Mode[]).map(m => (
          <button key={m} onClick={() => setMode(m)}
            style={{
              fontSize: 12, padding: "5px 14px", borderRadius: 999, cursor: "pointer",
              border: mode === m ? "1px solid var(--primary)" : "1px solid var(--border)",
              background: mode === m ? "rgba(37, 99, 235, 0.1)" : "var(--bg)",
              color: mode === m ? "var(--primary)" : "var(--muted)", fontWeight: mode === m ? 700 : 500,
            }}>
            {m === "review" ? `Review${pendingCount ? ` · ${pendingCount} to do` : ""}` : "Timeline"}
          </button>
        ))}
        <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: "auto" }}>
          {draftCount} claims in draft
        </span>
      </div>
      {mode === "review"
        ? <ClaimsReview claims={profile.claims} allClaims={profile.claims} profile={profile} onProfileUpdate={onProfileUpdate} emptyMessage="No claims have been collected." />
        : <TimelineTab profile={profile} onProfileUpdate={onProfileUpdate} onLoadSuggestions={onLoadSuggestions} />}
    </div>
  );
}
