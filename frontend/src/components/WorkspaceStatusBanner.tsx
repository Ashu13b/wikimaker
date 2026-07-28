import type { WikiStatus } from "../types";
import { getWorkspaceRoute } from "../workflow";

export default function WorkspaceStatusBanner({ wikiStatus }: { wikiStatus: WikiStatus }) {
  const route = getWorkspaceRoute(wikiStatus.status);

  return (
    <section className={`workspace-status workspace-status-${route.tone}`} aria-label="Wikimedia workflow status">
      <div className="workspace-status-heading">
        <span className="workspace-mode-badge">{route.label}</span>
        {wikiStatus.url && (
          <a href={wikiStatus.url} target="_blank" rel="noreferrer">
            Open Wikimedia page ↗
          </a>
        )}
      </div>
      <p>{route.description}</p>
      {wikiStatus.note && <p className="workspace-status-note">{wikiStatus.note}</p>}
    </section>
  );
}
