import { useState } from "react";
import { targetedSearch } from "../api";
import type { PersonProfile, Source } from "../types";

const TIMELINE_FIELDS = ["birth_date", "education", "affiliation", "position", "award", "death_date"];

const FIELD_COLOR: Record<string, string> = {
  birth_date:  "#6366f1",
  death_date:  "#6b7280",
  education:   "#8b5cf6",
  affiliation: "#0891b2",
  position:    "#0d9488",
  award:       "#d97706",
  known_for:   "#16a34a",
};

const FIELD_LABEL: Record<string, string> = {
  birth_date:  "Birth",
  death_date:  "Death",
  education:   "Education",
  affiliation: "Affiliation",
  position:    "Position",
  award:       "Award",
  known_for:   "Known for",
};

function parseFirstYear(s: string | null | undefined): number | null {
  if (!s) return null;
  const m = s.match(/\b(1[89]\d\d|20\d\d)\b/);
  return m ? parseInt(m[1]) : null;
}

export default function TimelineTab({ profile, onProfileUpdate, onLoadSuggestions }: {
  profile: PersonProfile;
  onProfileUpdate?: (p: PersonProfile) => void;
  onLoadSuggestions?: () => void;
}) {
  // Build event list from temporal claims
  interface TLEvent {
    year: number | null;
    period: string;
    text: string;
    field: string;
    source: Source | null;
    source_url: string | null;
  }

  const events: TLEvent[] = [];

  // Birth from profile-level field (may not have a claim)
  if (profile.birth_date && !profile.claims.some(c => c.field === "birth_date")) {
    events.push({
      year: parseFirstYear(profile.birth_date),
      period: profile.birth_date,
      text: `Born ${profile.birth_date}`,
      field: "birth_date",
      source: null,
      source_url: null,
    });
  }

  for (const claim of profile.claims) {
    if (!TIMELINE_FIELDS.includes(claim.field)) continue;
    const src = claim.source_url ? profile.sources.find(s => s.url === claim.source_url) ?? null : null;
    const year = parseFirstYear(claim.date_context) ?? parseFirstYear(claim.text);
    events.push({
      year,
      period: claim.date_context || "",
      text: claim.text,
      field: claim.field,
      source: src,
      source_url: claim.source_url ?? null,
    });
  }

  const dated   = events.filter(e => e.year !== null).sort((a, b) => a.year! - b.year!);
  const undated = events.filter(e => e.year === null);

  // Find gaps in dated events (adaptive thresholds)
  interface GapInfo {
    isGap: true;
    startYear: number;
    endYear: number;
    gapYears: number;
  }

  const birthYear = profile.birth_date ? parseFirstYear(profile.birth_date) : null;
  const datedRows: (TLEvent | GapInfo)[] = [];

  if (dated.length > 0) {
    let lastYear = dated[0].year!;
    datedRows.push(dated[0]);

    for (let i = 1; i < dated.length; i++) {
      const ev = dated[i];
      const currentYear = ev.year!;
      
      // Adaptive threshold: 18 years for childhood (<= birthYear + 22), 3 years for active career
      const threshold = (birthYear && currentYear <= birthYear + 22) ? 18 : 3;

      if (currentYear - lastYear > threshold) {
        datedRows.push({
          isGap: true,
          startYear: lastYear,
          endYear: currentYear,
          gapYears: currentYear - lastYear,
        });
      }
      datedRows.push(ev);
      lastYear = Math.max(lastYear, currentYear);
    }

    // Check gap to present year (if no death_date field or claim)
    const hasDeathDate = profile.claims.some(c => c.field === "death_date");
    const presentYear = new Date().getFullYear();
    if (!hasDeathDate) {
      const threshold = (birthYear && presentYear <= birthYear + 22) ? 18 : 3;
      if (presentYear - lastYear > threshold) {
        datedRows.push({
          isGap: true,
          startYear: lastYear,
          endYear: presentYear,
          gapYears: presentYear - lastYear,
        });
      }
    }
  }

  // Compute timeline boundaries for the density heatmap
  const minYear = birthYear ?? (dated.length > 0 ? dated[0].year! : null);
  const maxYear = new Date().getFullYear();
  const totalSpan = minYear ? maxYear - minYear : 0;
  const gaps = datedRows.filter((r): r is GapInfo => 'isGap' in r);

  if (events.length === 0) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
        No timeline events yet. Confirm sources to extract claims with dates.
      </div>
    );
  }
  function EventRow({ ev }: { ev: TLEvent }) {
    const color = FIELD_COLOR[ev.field] ?? "#6b7280";
    const dotStyle: string = ev.source?.reliability === "reliable_secondary"
      ? "solid"
      : ev.source ? "primary" : "empty";
    return (
      <div style={{ display: "flex", gap: 0, marginBottom: 10, position: "relative" }}>
        {/* Year column */}
        <div style={{ width: 52, flexShrink: 0, paddingTop: 2 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: ev.year ? color : "var(--muted)" }}>
            {ev.period || "—"}
          </span>
        </div>
        {/* Dot + line */}
        <div style={{ width: 20, flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{
            width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
            marginTop: 3,
            background: dotStyle === "solid" ? color : dotStyle === "primary" ? "white" : "var(--bg)",
            border: `2px solid ${dotStyle === "empty" ? "var(--muted)" : color}`,
            boxShadow: dotStyle === "solid" ? `0 0 0 2px ${color}30` : "none",
          }} />
          <div style={{ flex: 1, width: 2, background: "var(--border)", minHeight: 8 }} />
        </div>
        {/* Content */}
        <div style={{ flex: 1, paddingLeft: 8, paddingBottom: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
            <span style={{ fontSize: 10, fontWeight: 700, color, background: `${color}15`, borderRadius: 4, padding: "1px 5px" }}>
              {FIELD_LABEL[ev.field] ?? ev.field}
            </span>
            {!ev.source && ev.source_url === null && (
              <span style={{ fontSize: 10, color: "var(--warning)", fontWeight: 600 }}>no source</span>
            )}
          </div>
          <p style={{ fontSize: 13, margin: 0, lineHeight: 1.4 }}>{ev.text}</p>
          {ev.source && (
            <a href={ev.source_url!} target="_blank" rel="noreferrer"
              style={{ fontSize: 11, color: "var(--primary)", marginTop: 2, display: "inline-block" }}>
              {ev.source.publisher || new URL(ev.source_url!).hostname.replace("www.", "")} ↗
            </a>
          )}
        </div>
      </div>
    );
  }

  function GapRow({ gap }: { gap: GapInfo }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMsg, setSuccessMsg] = useState<string | null>(null);

    async function handleFillGap() {
      if (!onProfileUpdate) return;
      setLoading(true);
      setError(null);
      setSuccessMsg(null);
      try {
        const queryHint = `${gap.startYear} ${gap.endYear}`;
        
        // Concurrent multi-slot search (position + award)
        const [respPos, respAward] = await Promise.all([
          targetedSearch(profile.name, "position", queryHint),
          targetedSearch(profile.name, "award", queryHint)
        ]);

        // Merge sources and claims
        const mergedSources = [...respPos.sources];
        const existingUrls = new Set(mergedSources.map(s => s.url));
        for (const s of respAward.sources) {
          if (!existingUrls.has(s.url)) {
            mergedSources.push(s);
            existingUrls.add(s.url);
          }
        }

        const mergedClaims = [...respPos.new_claims];
        const existingClaims = new Set(mergedClaims.map(c => c.text));
        for (const c of respAward.new_claims) {
          if (!existingClaims.has(c.text)) {
            mergedClaims.push(c);
            existingClaims.add(c.text);
          }
        }

        onProfileUpdate({
          ...profile,
          sources: [...profile.sources, ...mergedSources],
          claims: [...profile.claims, ...mergedClaims],
          missing_slots: respPos.missing_slots,
          notability: respPos.notability,
        });

        const newSourcesCount = mergedSources.length;
        const newClaimsCount = mergedClaims.length;
        if (newSourcesCount > 0) {
          setSuccessMsg(`Found ${newSourcesCount} new source(s) and ${newClaimsCount} new claim(s) targeting ${gap.startYear}–${gap.endYear}!`);
          // Reactive suggestion sync
          onLoadSuggestions?.();
        } else {
          setSuccessMsg("Search completed, but no new sources were found for this period.");
        }
      } catch (err) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    }

    return (
      <div id={`gap-card-${gap.startYear}-${gap.endYear}`} style={{ display: "flex", gap: 0, marginBottom: 10, position: "relative" }}>
        {/* Year range column */}
        <div style={{ width: 52, flexShrink: 0, paddingTop: 4 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: "var(--warning)" }}>
            {gap.startYear}–{gap.endYear}
          </span>
        </div>
        {/* Dot + line column */}
        <div style={{ width: 20, flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
            marginTop: 8,
            background: "transparent",
            border: `2px dashed var(--warning)`,
          }} />
          <div style={{ flex: 1, width: 2, borderLeft: "2px dashed var(--warning)", minHeight: 40 }} />
        </div>
        {/* Content column */}
        <div style={{ flex: 1, paddingLeft: 8, paddingBottom: 12 }}>
          <div style={{
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: 8,
            padding: "10px 14px",
            boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
            marginTop: 2,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
              <div>
                <p style={{ fontSize: 12, fontWeight: 700, color: "#92400e", margin: 0 }}>
                  Timeline Gap: {gap.gapYears} years
                </p>
                <p style={{ fontSize: 11, color: "#b45309", margin: "2px 0 0" }}>
                  No sourced events found between {gap.startYear} and {gap.endYear}.
                </p>
              </div>
              {onProfileUpdate && (
                <button
                  onClick={handleFillGap}
                  disabled={loading}
                  style={{
                    fontSize: 11,
                    padding: "6px 12px",
                    background: "var(--warning)",
                    color: "#fff",
                    borderRadius: 6,
                    border: "none",
                    cursor: "pointer",
                    fontWeight: 700,
                  }}
                >
                  {loading ? "Searching..." : "Search to fill gap"}
                </button>
              )}
            </div>
            {error && (
              <p style={{ fontSize: 11, color: "var(--danger)", marginTop: 6, marginBottom: 0 }}>
                {error}
              </p>
            )}
            {successMsg && (
              <p style={{ fontSize: 11, color: "var(--success)", fontWeight: 600, marginTop: 6, marginBottom: 0 }}>
                {successMsg}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ paddingTop: 20 }}>
      {/* ── Density Heatmap Overview ── */}
      {minYear && totalSpan > 0 && (
        <div style={{ marginBottom: 24 }}>
          <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, color: "var(--muted)", marginBottom: 8 }}>
            Timeline Density Heatmap
          </p>
          <div style={{
            position: "relative",
            width: "100%",
            height: 32,
            background: "var(--border)30",
            borderRadius: 8,
            border: "1px solid var(--border)",
            overflow: "hidden",
            display: "flex",
            alignItems: "center"
          }}>
            {/* Render Gaps */}
            {gaps.map((gap, idx) => {
              const left = ((gap.startYear - minYear) / totalSpan) * 100;
              const width = ((gap.endYear - gap.startYear) / totalSpan) * 100;
              return (
                <div
                  key={`heatmap-gap-${idx}`}
                  title={`Gap: ${gap.startYear}-${gap.endYear} (${gap.gapYears} years)`}
                  style={{
                    position: "absolute",
                    left: `${left}%`,
                    width: `${width}%`,
                    height: "100%",
                    background: "rgba(245, 158, 11, 0.18)",
                    borderLeft: "1px dashed rgba(245, 158, 11, 0.4)",
                    borderRight: "1px dashed rgba(245, 158, 11, 0.4)",
                    transition: "background 0.2s",
                    cursor: "pointer"
                  }}
                  onClick={() => {
                    const el = document.getElementById(`gap-card-${gap.startYear}-${gap.endYear}`);
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  }}
                />
              );
            })}

            {/* Render Event ticks */}
            {dated.map((ev, idx) => {
              const left = ((ev.year! - minYear) / totalSpan) * 100;
              const color = FIELD_COLOR[ev.field] ?? "var(--primary)";
              return (
                <div
                  key={`heatmap-tick-${idx}`}
                  title={`${ev.period || ev.year}: ${ev.text}`}
                  style={{
                    position: "absolute",
                    left: `${left}%`,
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: color,
                    border: "1px solid #fff",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                    transform: "translateX(-50%)",
                    zIndex: 2,
                    cursor: "pointer"
                  }}
                />
              );
            })}
          </div>
          {/* Year labels */}
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--muted)", marginTop: 4, padding: "0 4px" }}>
            <span>{minYear}</span>
            <span>{Math.round(minYear + totalSpan / 2)}</span>
            <span>{maxYear}</span>
          </div>
        </div>
      )}

      {/* ── Event List ── */}
      <div style={{ position: "relative" }}>
        {datedRows.map((row, i) => {
          if ('isGap' in row) {
            return <GapRow key={`gap-${i}`} gap={row} />;
          } else {
            return <EventRow key={`ev-${i}`} ev={row} />;
          }
        })}
        {undated.length > 0 && (
          <>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, color: "var(--muted)", margin: "16px 0 10px 72px" }}>
              Undated
            </p>
            {undated.map((ev, i) => <EventRow key={`u${i}`} ev={ev} />)}
          </>
        )}
      </div>

      <div style={{ marginTop: 16, padding: "10px 12px", background: "var(--bg)", borderRadius: 8, fontSize: 11, color: "var(--muted)" }}>
        <strong>Legend:</strong>&nbsp;
        <span style={{ marginRight: 10 }}>Filled dot = reliable secondary source</span>
        <span style={{ marginRight: 10 }}>Outlined dot = primary/self-published</span>
        <span>Empty dot = no source yet</span>
      </div>
    </div>
  );
}

// ── Profile tab — Wikipedia slot view ────────────────────────────────────────
