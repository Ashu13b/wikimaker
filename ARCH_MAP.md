<!-- context-kit ARCH_MAP · v0.1.0 · generated 2026-07-29 15:39 UTC · sha 343c8bf · host vnic-trading -->

# ARCH_MAP

Top-level directories — what each is for + which dirs it imports. Consult before adding a cross-directory import; flagged cycles are architectural smells.

## Directories
- `./` — Process launchers and local browser integration. → `engine/`, `wiki/`
- `backend/` — FastAPI transport, session persistence, and workflow orchestration. → `./`, `engine/`, `wiki/`
- `engine/` — Domain services for identity, discovery, extraction, classification, and evidence analysis.
- `frontend/` — React presentation, client API adapters, and user-workflow interaction.
- `tests/` — _(unset — add to `.context-kit/purposes`)_ → `backend/`, `engine/`, `frontend/`, `wiki/`
- `wiki/` — Wikimedia status checks and wikitext rendering policy. → `engine/`
