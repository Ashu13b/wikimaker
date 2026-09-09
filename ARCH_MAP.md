<!-- context-kit ARCH_MAP · v0.2.0 · generated 2026-09-06 19:18 UTC · sha d578fd2 · host instance-20260819-0844 -->

# ARCH_MAP

Top-level directories — what each is for + which dirs it imports. Consult before adding a cross-directory import; flagged cycles are architectural smells.

## Directories
- `./` — Process launchers and local browser integration. → `engine/`
- `backend/` — FastAPI transport, session persistence, and workflow orchestration. → `./`, `engine/`, `scripts/`, `wiki/`
- `engine/` — Domain services for identity, discovery, extraction, classification, and evidence analysis.
- `frontend/` — React presentation, client API adapters, and user-workflow interaction. → `backend/`
- `scripts/` — Operational CLI utilities and offline automation scripts. → `engine/`, `wiki/`
- `tests/` — Unit, integration, and regression test suites. → `./`, `backend/`, `engine/`, `frontend/`, `scripts/`, `wiki/`
- `wiki/` — Wikimedia status checks and wikitext rendering policy. → `engine/`
