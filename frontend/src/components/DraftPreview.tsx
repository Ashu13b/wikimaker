import { useEffect, useState } from "react";
import { getDraftPreview } from "../api";

const PREVIEW_CSS = `
  html, body { margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 14px; line-height: 1.6; color: #202122; padding: 16px 20px; }
  .mw-parser-output { max-width: 900px; }
  .mw-parser-output a { color: #3366cc; text-decoration: none; }
  .mw-parser-output a:hover { text-decoration: underline; }
  .mw-parser-output h2 { font-family: Georgia, "Times New Roman", serif; font-size: 1.5em; border-bottom: 1px solid #a2a9b1; padding-bottom: 2px; margin: 20px 0 8px; }
  .mw-parser-output h3 { font-size: 1.2em; margin: 16px 0 6px; }
  .mw-parser-output h4 { font-size: 1em; margin: 14px 0 4px; }
  .mw-parser-output p { margin: 0.5em 0; }
  .mw-parser-output ul, .mw-parser-output ol { margin: 0.5em 0; padding-left: 1.6em; }
  .mw-parser-output .infobox { border: 1px solid #a2a9b1; background: #f8f9fa; float: right; clear: right; width: 22em; margin: 0 0 12px 16px; border-collapse: collapse; font-size: 0.95em; }
  .mw-parser-output .infobox th, .mw-parser-output .infobox td { border: 1px solid #a2a9b1; padding: 4px 8px; text-align: left; vertical-align: top; }
  .mw-parser-output .infobox caption { font-weight: bold; font-size: 1.1em; padding: 4px 8px; text-align: center; }
  .mw-parser-output .infobox-subheader { background: #eaecf0; font-weight: bold; }
  .mw-parser-output .reflist { font-size: 0.9em; margin-bottom: 0.5em; }
  .mw-parser-output .reflist ol { padding-left: 1.6em; }
  .mw-parser-output .reflist .references { font-size: 100%; }
  .mw-parser-output .thumb { margin: 0 0 12px 16px; border: 1px solid #c8ccd1; background: #f8f9fa; padding: 3px; }
  .mw-parser-output .thumbinner { font-size: 0.88em; }
  .mw-parser-output .thumbcaption { text-align: left; padding: 2px; }
  .mw-parser-output .hatnote { font-style: italic; margin: 0.8em 0; }
  .mw-parser-output .mw-editsection, .mw-parser-output .mw-editsection-like { display: none; }
  .mw-parser-output sup.reference { font-size: 0.8em; }
  .mw-parser-output .error { color: #d33; }
`;

interface Props {
  profileName: string;
  wikitext: string;
  draftDestination: { href: string; label: string };
}

export default function DraftPreview({ profileName, wikitext, draftDestination }: Props) {
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<"plain" | "afc" | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getDraftPreview(profileName)
      .then(h => { if (!cancelled) setHtml(h); })
      .catch(e => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [profileName]);

  async function copy(text: string, kind: "plain" | "afc") {
    if (!navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      setTimeout(() => setCopied(null), 2000);
    } catch { /* ignore clipboard failure */ }
  }

  const afcText = `{{subst:submit}}\n\n${wikitext}`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* AfC submission panel */}
      <div className="draft-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#eff6ff", border: "1px solid #bfdbfe", padding: "12px 16px", borderRadius: 8, gap: 12 }}>
        <div>
          <strong style={{ fontSize: 14, color: "#1e40af" }}>Reviewable Wikipedia Draft Loaded</strong>
          <p style={{ fontSize: 12, color: "#1e3a8a", margin: "2px 0 0" }}>
            Draft generated from approved evidence. Review Wikipedia notability, neutrality, and every citation before submission.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            className="btn-primary"
            onClick={() => copy(afcText, "afc")}
            style={{ fontSize: 13 }}
            title="Copies the draft with the {{subst:submit}} header that AfC expects"
          >
            {copied === "afc" ? "Copied for AfC!" : "Copy for AfC submission"}
          </button>
          <a href={draftDestination.href} target="_blank" rel="noopener noreferrer">
            <button className="btn-ghost" style={{ fontSize: 13 }}>
              {draftDestination.label} ↗
            </button>
          </a>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", fontSize: 13, padding: "32px 16px" }}>
          Rendering Wikipedia preview…
        </div>
      )}

      {error && (
        <div className="card">
          <p style={{ fontSize: 13, color: "var(--danger)", marginBottom: 8 }}>
            Wikipedia preview unavailable ({error}) — showing wikitext instead.
          </p>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 12, lineHeight: 1.6, color: "var(--text)", maxHeight: 420, overflow: "auto", background: "var(--bg)", borderRadius: 6, padding: 12 }}>
            {wikitext}
          </pre>
          <button className="btn-primary" onClick={() => copy(afcText, "afc")} style={{ fontSize: 13, marginTop: 12 }}>
            {copied === "afc" ? "Copied for AfC!" : "Copy for AfC submission"}
          </button>
        </div>
      )}

      {html && !error && (
        <>
          <iframe
            title="Wikipedia draft preview"
            sandbox="allow-popups"
            style={{ width: "100%", height: 720, border: "1px solid var(--border)", borderRadius: 8, background: "#fff" }}
            srcDoc={`<!DOCTYPE html><html><head><base href="https://en.wikipedia.org/" target="_blank"><meta charset="utf-8"><style>${PREVIEW_CSS}</style></head><body class="mw-parser-output">${html}</body></html>`}
          />
          <p style={{ fontSize: 11, color: "var(--muted)", margin: 0 }}>
            Rendered by Wikipedia's own renderer. Banner templates (like the AfC submission box) do not display in this preview —
            they appear once the draft is pasted on Wikipedia.
          </p>
        </>
      )}

      <div style={{ display: "flex", gap: 10 }}>
        <button className="btn-primary" onClick={() => copy(wikitext, "plain")}>
          {copied === "plain" ? "Copied Wikitext!" : "Copy Wikitext to Clipboard"}
        </button>
      </div>
    </div>
  );
}
