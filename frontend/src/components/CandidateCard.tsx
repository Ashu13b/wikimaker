import type { PersonCandidate } from "../types";

interface Props {
  candidate: PersonCandidate;
  onConfirm: () => void;
  onSkip: () => void;
  index: number;
  total: number;
}

export default function CandidateCard({ candidate, onConfirm, onSkip, index, total }: Props) {
  return (
    <div className="card" style={{ maxWidth: 520, margin: "0 auto" }}>
      <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
        Candidate {index + 1} of {total} — Is this the right person?
      </p>

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
        <div style={{
          width: 80, height: 80, borderRadius: 8,
          background: "var(--bg)", border: "1px solid var(--border)",
          overflow: "hidden", flexShrink: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          {candidate.photo_url
            ? <img src={candidate.photo_url} alt={candidate.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            : <span style={{ fontSize: 32, color: "var(--muted)" }}>?</span>
          }
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{candidate.name}</h2>
          {(candidate.field || candidate.nationality || candidate.birth_year) && (
            <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8 }}>
              {[candidate.field, candidate.nationality, candidate.birth_year && `b. ${candidate.birth_year}`]
                .filter(Boolean).join(" · ")}
            </p>
          )}
          {candidate.affiliation && (
            <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8 }}>{candidate.affiliation}</p>
          )}
          <p style={{ fontSize: 13, lineHeight: 1.5 }}>{candidate.bio_snippet || "No description available."}</p>
          {candidate.wikipedia_url && (
            <a href={candidate.wikipedia_url} target="_blank" rel="noreferrer"
              style={{ fontSize: 12, color: "var(--primary)", marginTop: 8, display: "inline-block" }}>
              Wikipedia page exists →
            </a>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
        <button className="btn-primary" onClick={onConfirm} style={{ flex: 1 }}>
          Yes, this is the person
        </button>
        <button className="btn-ghost" onClick={onSkip}>
          Not this one
        </button>
      </div>
    </div>
  );
}
