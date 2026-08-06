export default function ResearchOperationsCard({ ops, drafting }: { ops: Record<string, boolean>; drafting: boolean }) {
  const items = [
    {
      id: "suggester",
      name: "Source Suggester",
      active: !!ops.suggester,
      descActive: "Generating web search queries for missing slots and fetching candidate URLs...",
      descIdle: "Idle · Ready to find new profile sources"
    },
    {
      id: "classifier",
      name: "Relevance Classifier",
      active: !!ops.classifier,
      descActive: "Analyzing webpage snippet, title, and publisher to verify name and context match...",
      descIdle: "Idle · Ready to filter out wrong-person pages"
    },
    {
      id: "extractor",
      name: "Fact Extractor",
      active: !!ops.extractor,
      descActive: "Extracting timeline events, affiliations, awards, and verifying dates...",
      descIdle: "Idle · Ready to parse confirmed sources"
    },
    {
      id: "idSync",
      name: "Researcher ID Sync",
      active: !!ops.idSync,
      descActive: "Searching for ORCID, Google Scholar, Semantic Scholar IDs and syncing works...",
      descIdle: "Idle · Ready to sync researcher profiles"
    },
    {
      id: "crawler",
      name: "Deep Crawler",
      active: !!ops.crawler,
      descActive: "Crawling outward from seed URLs to discover linked pages...",
      descIdle: "Idle · Ready for targeted crawling"
    },
    {
      id: "drafter",
      name: "Wikitext Drafter",
      active: drafting,
      descActive: "Rendering approved, source-linked claims into deterministic Wikipedia markup...",
      descIdle: "Idle · Ready to draft article"
    }
  ];

  return (
    <div className="card" style={{ padding: "16px", borderRadius: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: 16 }}>🤖</span>
        <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Research operations</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map(item => (
          <div key={item.id} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 11.5 }}>
            <span style={{
              width: 8, height: 8, borderRadius: "50%", marginTop: 4, flexShrink: 0,
              backgroundColor: item.active ? "#22c55e" : "#cbd5e1",
              boxShadow: item.active ? "0 0 8px #22c55e" : "none",
              transition: "all 0.3s ease"
            }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontWeight: 600, color: item.active ? "var(--text)" : "var(--muted)" }}>{item.name}</span>
                {item.active && (
                  <span style={{ fontSize: 10, color: "#22c55e", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>Active</span>
                )}
              </div>
              <p style={{ margin: "2px 0 0", color: item.active ? "var(--text)" : "var(--muted)", lineHeight: 1.35, fontSize: 11 }}>
                {item.active ? item.descActive : item.descIdle}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
