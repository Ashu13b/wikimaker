import type { WikiStatus } from "./types";

export type WorkspaceMode = "new_article" | "improve_draft" | "improve_article" | "deletion_review";
export type WorkspaceTone = "info" | "success" | "warning" | "danger";

export interface WorkspaceRoute {
  mode: WorkspaceMode;
  label: string;
  description: string;
  tone: WorkspaceTone;
  draftLabel: string | null;
}

const ROUTES: Record<WikiStatus["status"], WorkspaceRoute> = {
  clear: {
    mode: "new_article",
    label: "New article research",
    description: "No matching English Wikipedia article or draft was found. Build evidence first, then prepare an AfC draft.",
    tone: "success",
    draftLabel: "Generate AfC draft →",
  },
  draft: {
    mode: "improve_draft",
    label: "Existing draft improvement",
    description: "A draft already exists. Research should improve that draft rather than create a competing one.",
    tone: "warning",
    draftLabel: "Generate revised draft →",
  },
  exists: {
    mode: "improve_article",
    label: "Existing article research",
    description: "An article already exists. Audit its claims, citations, gaps, and possible improvements; duplicate draft generation is disabled.",
    tone: "info",
    draftLabel: null,
  },
  deleted: {
    mode: "deletion_review",
    label: "Deletion review",
    description: "A previous deletion was found. Review its history and new independent coverage before considering another draft.",
    tone: "danger",
    draftLabel: null,
  },
};

export function getWorkspaceRoute(status: WikiStatus["status"]): WorkspaceRoute {
  return ROUTES[status];
}

export function canGenerateDraft(status: WikiStatus["status"], hasVerifiedSources: boolean): boolean {
  return hasVerifiedSources && getWorkspaceRoute(status).draftLabel !== null;
}

export function getDraftDestination(wikiStatus: WikiStatus): { href: string; label: string } {
  if (wikiStatus.status === "draft" && wikiStatus.url) {
    return { href: wikiStatus.url, label: "Open existing draft →" };
  }
  return {
    href: "https://en.wikipedia.org/wiki/Wikipedia:Articles_for_creation/submissions",
    label: "Submit to AfC →",
  };
}
