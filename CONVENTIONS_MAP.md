<!-- context-kit CONVENTIONS_MAP · v0.1.0 · generated 2026-08-18 11:19 UTC · sha ff7ced3 · host vnic-trading -->

# CONVENTIONS_MAP

Declared house style — naming and structure rules for new code in this repo. Advisory (taste isn't gated); layering rules live in ARCH_MAP / `.context-kit/boundaries`.

- Drafting must remain deterministic and server-owned in wiki/draft.py; no fabricated or LLM-generated prose.
- Only human-confirmed and explicitly draft-approved claims backed by verified sources can enter wikitext.
- Test suites must remain isolated via temporary SESSIONS_DIR fixtures and never touch live user sessions.
- Keep strict type safety across backend (pyright) and frontend (tsc --noEmit).
- Mutations to in-memory session profiles must be serialized under store._lock before disk snapshot.
