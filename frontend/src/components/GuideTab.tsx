import { useState } from "react";

export default function GuideTab() {
  const [activeSection, setActiveSection] = useState<string>("all");

  const buttonItems = [
    {
      group: "Claim Review & Triage",
      badge: "+ Draft",
      badgeStyle: { background: "rgba(22, 163, 74, 0.15)", color: "var(--success)", border: "1px solid rgba(22, 163, 74, 0.3)" },
      title: "Approve & Include in Draft",
      meaning: "Adds this exact fact into the Wikipedia wikitext article. Only click this for notable, encyclopedic facts that are supported by a verified source.",
      whenToUse: "When you want Wikipedia readers to see this fact in the published biography.",
    },
    {
      group: "Claim Review & Triage",
      badge: "✓ Dossier",
      badgeStyle: { background: "rgba(37, 99, 235, 0.12)", color: "var(--primary)", border: "1px solid rgba(37, 99, 235, 0.3)" },
      title: "Confirm for Research Dossier Only",
      meaning: "Saves this fact into your background research dossier / markdown notes, but keeps it OUT of the Wikipedia draft.",
      whenToUse: "For minor details, routine dates, or background facts that are true, but would clutter or weaken a concise Wikipedia article.",
    },
    {
      group: "Claim Review & Triage",
      badge: "✎",
      badgeStyle: { background: "#f1f5f9", color: "var(--text)", border: "1px solid var(--border)" },
      title: "Edit / Draft Wording",
      meaning: "Allows you to edit either the raw claim fact or polish the exact encyclopedic wording (paraphrase) rendered in Wikipedia.",
      whenToUse: "When an AI-extracted fact needs better phrasing, corrected dates, or a more neutral tone.",
    },
    {
      group: "Claim Review & Triage",
      badge: "− Draft",
      badgeStyle: { background: "rgba(220, 38, 38, 0.12)", color: "var(--danger)", border: "1px solid rgba(220, 38, 38, 0.3)" },
      title: "Remove from Draft",
      meaning: "Removes the fact from the Wikipedia article, but keeps it safely preserved in your research dossier.",
      whenToUse: "When you decide a draft sentence is redundant or too detailed for Wikipedia.",
    },
    {
      group: "Claim Review & Triage",
      badge: "✗",
      badgeStyle: { background: "rgba(220, 38, 38, 0.12)", color: "var(--danger)", border: "1px solid rgba(220, 38, 38, 0.3)" },
      title: "Skip / Reject",
      meaning: "Completely ignores and excludes this claim from both the draft and dossier.",
      whenToUse: "When a claim is inaccurate, about the wrong namesake person, or pure noise.",
    },
    {
      group: "Claim Review & Triage",
      badge: "+ Approve all usable for draft",
      badgeStyle: { background: "rgba(22, 163, 74, 0.15)", color: "var(--success)", border: "1px solid rgba(22, 163, 74, 0.3)" },
      title: "Batch Approve Usable",
      meaning: "In 1 click, approves all unreviewed facts backed by verified sources directly into the draft.",
      whenToUse: "When you have verified trusted sources and want to rapidly draft all valid findings.",
    },
    {
      group: "Source Management",
      badge: "Verify Source",
      badgeStyle: { background: "rgba(37, 99, 235, 0.12)", color: "var(--primary)", border: "1px solid rgba(37, 99, 235, 0.3)" },
      title: "Human Source Verification",
      meaning: "Marks that you have reviewed this webpage/link and confirmed it is genuine and genuinely discusses this subject.",
      whenToUse: "Required before any claims from that source can be added to the Wikipedia draft.",
    },
    {
      group: "Source Management",
      badge: "Auto-enrich",
      badgeStyle: { background: "#f1f5f9", color: "var(--text)", border: "1px solid var(--border)" },
      title: "Automated Search Sweep",
      meaning: "Launches targeted searches for news reports, academic papers, books, and university directories.",
      whenToUse: "At the start of research or when you need more independent secondary sources.",
    },
    {
      group: "Source Management",
      badge: "Check Liveness",
      badgeStyle: { background: "#f1f5f9", color: "var(--text)", border: "1px solid var(--border)" },
      title: "Verify URL Health",
      meaning: "Tests every cited web link to verify it is alive (HTTP 200) and detects dead links or redirect traps.",
      whenToUse: "Before generating a draft, to ensure Wikipedia reviewers won't find broken references.",
    },
    {
      group: "Draft & Submission",
      badge: "Generate Draft",
      badgeStyle: { background: "var(--primary)", color: "#fff" },
      title: "Render Wikipedia Wikitext",
      meaning: "Runs the deterministic wikitext engine to produce standard Wikipedia markup strictly from your approved claims.",
      whenToUse: "When you have reviewed your claims and the Draft Readiness checklist shows green.",
    },
    {
      group: "Draft & Submission",
      badge: "Copy for AfC (with {{subst:submit}})",
      badgeStyle: { background: "var(--primary)", color: "#fff" },
      title: "1-Click Wikipedia Submission",
      meaning: "Copies the full wikitext with Wikipedia's submission template already attached at the top.",
      whenToUse: "When pasting into Wikipedia's Articles for Creation submission form.",
    },
  ];

  const filteredButtons = activeSection === "all"
    ? buttonItems
    : buttonItems.filter(b => b.group.toLowerCase().includes(activeSection.toLowerCase()));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, paddingBottom: 40 }}>
      {/* Hero Banner */}
      <div className="card" style={{ background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)", color: "#fff", border: "none" }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>How Wikimaker Works & Button Guide</h2>
        <p style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6, maxWidth: 740, margin: 0 }}>
          Wikimaker helps you research a notable person, collect reliable evidence, and create a Wikipedia-ready draft. 
          Here is how the entire system works and exactly what every button does.
        </p>
      </div>

      {/* 4-Stage Workflow Cards */}
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>The 4-Step Research Journey</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
          <div className="card" style={{ borderTop: "4px solid #3b82f6" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#3b82f6", textTransform: "uppercase", marginBottom: 6 }}>Step 1: Identify</div>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px" }}>Disambiguate the Subject</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5, margin: 0 }}>
              Enter the person's name and affiliation. The system checks Wikipedia and Wikidata so you don't research a namesake or duplicate an existing article.
            </p>
          </div>

          <div className="card" style={{ borderTop: "4px solid #10b981" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#10b981", textTransform: "uppercase", marginBottom: 6 }}>Step 2: Collect Sources</div>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px" }}>Verify Web & News Links</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5, margin: 0 }}>
              Review discovered web pages. Click <strong>Verify Source</strong> on valid links. The system automatically tags sources as Independent News, Academic, or Primary.
            </p>
          </div>

          <div className="card" style={{ borderTop: "4px solid #8b5cf6" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#8b5cf6", textTransform: "uppercase", marginBottom: 6 }}>Step 3: Review Claims</div>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px" }}>Draft vs. Dossier Triage</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5, margin: 0 }}>
              Choose what goes into the Wikipedia article (<strong>+ Draft</strong>) vs what stays in your background research notes (<strong>✓ Dossier</strong>).
            </p>
          </div>

          <div className="card" style={{ borderTop: "4px solid #f59e0b" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#f59e0b", textTransform: "uppercase", marginBottom: 6 }}>Step 4: Draft & Submit</div>
            <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px" }}>Render & Copy Wikitext</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5, margin: 0 }}>
              The system audits evidence requirements (2+ independent news sources), checks links, formats citations, and generates standard Wikipedia wikitext.
            </p>
          </div>
        </div>
      </div>

      {/* Draft vs Dossier Key Concept */}
      <div className="card" style={{ background: "rgba(37, 99, 235, 0.04)", border: "1px solid rgba(37, 99, 235, 0.2)" }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--primary)", marginBottom: 8 }}>
          💡 The Most Important Concept: "In Draft" vs. "Dossier Only"
        </h3>
        <p style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.6, marginBottom: 12 }}>
          Wikipedia articles get rejected when they contain routine resumes, promotional trivia, or unverified claims. Wikimaker solves this with two distinct destination buckets:
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ padding: 12, background: "#fff", borderRadius: 8, border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--success)", display: "block", marginBottom: 4 }}>
              📌 In Draft (+ Draft)
            </span>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              For <strong>notable milestones, major awards, breakthrough publications, and verifiable achievements</strong>. These are compiled directly into the Wikipedia wikitext article.
            </p>
          </div>
          <div style={{ padding: 12, background: "#fff", borderRadius: 8, border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "#475569", display: "block", marginBottom: 4 }}>
              📁 Dossier Only (✓ Dossier)
            </span>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              For <strong>background facts, routine employment dates, minor trivia, and research leads</strong>. These are preserved in your exportable research report without bloating the Wikipedia article.
            </p>
          </div>
        </div>
      </div>

      {/* Button & Action Guide */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px" }}>What Every Button Means</h3>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>Click a category filter to see specific button actions.</p>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {["all", "claim", "source", "draft"].map(cat => (
              <button
                key={cat}
                onClick={() => setActiveSection(cat)}
                style={{
                  fontSize: 11, fontWeight: 700, padding: "4px 10px", borderRadius: 6,
                  background: activeSection === cat ? "var(--primary)" : "transparent",
                  color: activeSection === cat ? "#fff" : "var(--muted)",
                  border: activeSection === cat ? "none" : "1px solid var(--border)",
                }}
              >
                {cat === "all" ? "All Buttons" : cat === "claim" ? "Claims" : cat === "source" ? "Sources" : "Draft"}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {filteredButtons.map((btn, idx) => (
            <div key={idx} style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 8, background: "#fff" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
                <span style={{ fontSize: 12, fontWeight: 700, padding: "3px 9px", borderRadius: 5, ...btn.badgeStyle }}>
                  {btn.badge}
                </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>
                  {btn.title}
                </span>
                <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: "auto" }}>
                  {btn.group}
                </span>
              </div>
              <p style={{ fontSize: 12, color: "var(--text)", margin: "0 0 4px", lineHeight: 1.5 }}>
                <strong>What it does:</strong> {btn.meaning}
              </p>
              <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
                <strong>When to use:</strong> {btn.whenToUse}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Frequently Asked Questions */}
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>Frequently Asked Questions</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: Why is the "+ Draft" button greyed out on some claims?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              Wikipedia strictly requires that every assertion has a human-verified source. If the source hasn't been verified yet, or if it is flagged as unreliable, the button is disabled until you verify the source in the Sources tab.
            </p>
          </div>
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: What is the difference between an Independent News source and a Primary source?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              An <strong>Independent Secondary source</strong> (e.g. The Hindu, The Tribune, NDTV) is third-party journalism that proves Wikipedia notability (WP:GNG). A <strong>Primary source</strong> (e.g. the person's university profile or CV) can verify basic employment dates, but cannot prove notability on its own.
            </p>
          </div>
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: What belongs in "In Draft" vs "Dossier Only"?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 6px", lineHeight: 1.5 }}>
              • <strong>In Draft (+ Draft):</strong> Encyclopedic milestones meeting Wikipedia standards (major awards, significant independent press-covered discoveries, verified appointments). Keep articles concise and neutral.
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              • <strong>Dossier Only (✓ Dossier):</strong> Background research archive for humans. Include comprehensive paper lists, routine committee seats, CV details, and uncorroborated quotes that are useful for research but would be rejected as trivial or promotional on Wikipedia.
            </p>
          </div>
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: Why do some verified sources have 0 claims extracted?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              When a source is verified, the system checks for new encyclopedic claims. A source shows 0 claims if: (1) <strong>Already Backed / Redundant:</strong> The article repeats facts already captured in your session (e.g. syndicated wire copies), (2) <strong>Passing Mention:</strong> The page mentions the subject in a committee or co-author list without narrative biographical facts, or (3) <strong>Thin Snippet:</strong> Content was paywalled or too brief. You can always click <em>+ Add Sourced Claim</em> to manually record facts you read on the page.
            </p>
          </div>
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: What should I do when I am ready to submit the article to Wikipedia?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              Click <strong>"Generate Draft"</strong>, inspect the Wikipedia preview, then click <strong>"Copy for AfC (with &#123;&#123;subst:submit&#125;&#125;)"</strong>. Paste that directly into the Wikipedia Articles for Creation submission box.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
