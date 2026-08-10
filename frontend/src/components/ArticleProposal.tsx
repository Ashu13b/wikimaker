import { useState, useEffect } from "react";
import type { ArticleProposal } from "../api";
import { getArticleProposal } from "../api";

export default function ArticleProposalView({ profileName }: { profileName: string }) {
  const [proposal, setProposal] = useState<ArticleProposal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getArticleProposal(profileName)
      .then(p => { if (!cancelled) setProposal(p); })
      .catch(e => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [profileName]);

  if (loading) {
    return (
      <div className="card" style={{ marginTop: 16, fontSize: 13, color: "var(--muted)", padding: "18px 20px" }}>
        Comparing your confirmed claims against the live article…
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ marginTop: 16, fontSize: 13, color: "var(--danger)" }}>
        Could not build the article proposal: {error}
      </div>
    );
  }

  if (!proposal) return null;

  const additions = proposal.coverage.filter(c => !c.covered);
  const covered = proposal.coverage.filter(c => c.covered);

  return (
    <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div className="card" style={{ borderLeft: "4px solid var(--primary)", background: "linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%)" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
          <h2 style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>Edit proposal for “{proposal.article_title}”</h2>
          <a href={proposal.article_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>Open article ↗</a>
        </div>
        <p style={{ fontSize: 13, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
          {covered.length} confirmed fact{covered.length === 1 ? "" : "s"} already covered ·{" "}
          <strong style={{ color: "var(--warning)" }}>{additions.length} candidate addition{additions.length === 1 ? "" : "s"}</strong>{" "}
          found in your verified sources but not in the article. The matching is token-based — review each addition before editing.
        </p>
      </div>

      {/* Candidate additions */}
      <div className="card">
        <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>
          Suggested additions ({additions.length})
        </p>
        <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 12px" }}>
          Each is a confirmed claim with a human-verified source. Add these to the article with an inline citation.
        </p>
        {additions.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--success)", margin: 0 }}>
            Everything you confirmed already appears in the article — nothing to add.
          </p>
        )}
        {additions.map(c => (
          <div key={c.claim_index} style={{ padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "baseline", marginBottom: 3 }}>
              <span style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--muted)" }}>
                {c.field}
              </span>
              {c.date_context && (
                <span style={{ fontSize: 11, color: "var(--muted)", fontStyle: "italic" }}>{c.date_context}</span>
              )}
              <span style={{ fontSize: 10, color: "var(--warning)", fontWeight: 700, marginLeft: "auto" }}>
                match {Math.round(c.score * 100)}%
              </span>
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.5, margin: "0 0 4px" }}>{c.text}</p>
            {c.source_url && (
              <a href={c.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>Source ↗</a>
            )}
          </div>
        ))}
      </div>

      {/* Already covered */}
      {covered.length > 0 && (
        <div className="card">
          <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>
            Already covered by the article ({covered.length})
          </p>
          {covered.map(c => (
            <div key={c.claim_index} style={{ display: "flex", gap: 8, padding: "6px 0", fontSize: 12, color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>
              <span style={{ color: "var(--success)", fontWeight: 700, flexShrink: 0 }}>✓</span>
              <span style={{ flex: 1, minWidth: 0 }}>{c.text}</span>
              <span style={{ fontSize: 10, flexShrink: 0 }}>{Math.round(c.score * 100)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
