<!-- context-kit ARCH_MAP · v0.1.0 · generated 2026-08-18 18:42 UTC · sha ff7ced3 · host vnic-trading -->

# ARCH_MAP

Top-level directories — what each is for + which dirs it imports. Consult before adding a cross-directory import; flagged cycles are architectural smells.

## Directories
- `./` — Process launchers and local browser integration. → `engine/`, `wiki/`
- `backend/` — FastAPI transport, session persistence, and workflow orchestration. → `./`, `engine/`, `wiki/`
- `engine/` — Domain services for identity, discovery, extraction, classification, and evidence analysis.
- `frontend/` — React presentation, client API adapters, and user-workflow interaction.
- `scripts/` — _(unset — add to `.context-kit/purposes`)_
- `tests/` — Unit, integration, and regression test suites. → `./`, `backend/`, `engine/`, `frontend/`, `wiki/`
- `wiki/` — Wikimedia status checks and wikitext rendering policy. → `./`, `engine/`

## Cycles
- `./` → `wiki/` closes a cycle — consider breaking this edge
- `wiki/` → `./` closes a cycle — consider breaking this edge
