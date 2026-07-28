import { useState } from "react";

export default function BookmarkletCard() {
  const [copied, setCopied] = useState(false);
  const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3890";
  const code = `javascript:(function(){const url=window.location.href;const text=document.body.innerText.slice(0,30000);const target='${origin}/?relay_url='+encodeURIComponent(url)+'&relay_text='+encodeURIComponent(text);window.open(target,'_blank');})();`;

  function handleCopy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div style={{ background: "rgba(37,99,235,0.05)", border: "1px dashed rgba(37,99,235,0.3)", borderRadius: 8, padding: "14px", marginBottom: 12 }}>
      <span style={{ fontWeight: 700, color: "var(--primary)", fontSize: 13, display: "block", marginBottom: 6 }}>
        💡 Direct Bookmarklet Import
      </span>
      <p style={{ color: "var(--muted)", fontSize: 12, lineHeight: 1.4, marginBottom: 10 }}>
        Extract and import web pages (ORCID, Google Scholar, university profiles) directly from your mobile browser tabs using a bookmarklet.
      </p>

      {/* Copy Code Action */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
        <textarea
          readOnly
          value={code}
          style={{ width: "100%", height: 60, fontSize: 11, fontFamily: "monospace", padding: 8, borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg)", resize: "none" }}
          onClick={e => (e.target as any).select()}
        />
        <button className="btn-primary" onClick={handleCopy} style={{ fontSize: 12, padding: "8px 12px", width: "100%" }}>
          {copied ? "✓ Copied JavaScript Code!" : "📋 Copy Bookmarklet Code"}
        </button>
      </div>

      {/* Step by step mobile instructions */}
      <div style={{ fontSize: 11, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
        <p style={{ fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>How to set up in Mobile Chrome:</p>
        <ol style={{ paddingLeft: 16, color: "var(--muted)", lineHeight: 1.4, marginBottom: 0 }}>
          <li>Tap the copy button above to copy the bookmarklet code.</li>
          <li>Bookmark this page (tap Chrome menu ⋮ → star icon ★).</li>
          <li>Edit the bookmark (tap "Edit" or menu ⋮ → Bookmarks → find this bookmark → ⋮ → Edit).</li>
          <li>Change the Name to: <strong style={{ color: "var(--text)" }}>Import to Wikimaker</strong>.</li>
          <li>Paste the copied code into the <strong>URL</strong> field, and save.</li>
        </ol>
        <p style={{ fontWeight: 600, color: "var(--text)", marginTop: 8, marginBottom: 4 }}>How to run on other websites:</p>
        <ol style={{ paddingLeft: 16, color: "var(--muted)", lineHeight: 1.4, marginBottom: 0 }}>
          <li>Go to any webpage (e.g. your candidate's biography, paper page).</li>
          <li>Tap Chrome's address bar.</li>
          <li>Type <strong style={{ color: "var(--text)" }}>Import to Wikimaker</strong>.</li>
          <li>Tap the autocomplete bookmark suggestion that appears with the star icon.</li>
          <li>Chrome will run the script, read the page, and redirect you back here with the source loaded!</li>
        </ol>
      </div>
    </div>
  );
}
