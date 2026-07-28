<!-- context-kit WORKFLOW · v0.1.0 · generated 2026-07-10 11:09 UTC · sha a91db49 · host vnic-trading -->

# WORKFLOW

Rigor profile: **standard** — change via `.context-kit/profile` (`light`|`standard`|`strict`), then `ck build`.

For non-trivial tasks, **start in plan mode** and get a quick go-ahead before coding.
Then loop per change:
0. Orient — consult CODE_MAP / ARCH_MAP / DEPS_MAP / DOCS_MAP / COMMANDS_MAP / CONVENTIONS_MAP / ENV_MAP before Grep/Read; don't re-derive what a map already states.
1. Implement a small slice.
2. Typecheck — pyright/mypy (py), tsc (ts), `go vet`, `cargo check`. Fix diagnostics.
3. Test the affected paths — pytest / vitest / `go test` / `cargo test`.
4. Verify via the actual CLI/UI when possible — it catches what unit tests miss.
5. Document public APIs; consult library docs before using unfamiliar ones.
6. When you learn a *why* or reject an approach, record it in AGENT_KNOWLEDGE.md.

On session start: if ROADMAP.md / AGENT_KNOWLEDGE.md are still empty scaffolds, recover their intent from git history / README / existing docs before new work — but if the repo has little history (a young project), ask the human (what is this for / what's next / what's deliberately out of scope) and record their answers; never invent roadmap or rationale from source. If the banner flags a long gap or large uncommitted diff, reconcile their `Next`/`Half-done` sections with the actual state first — intent doesn't auto-refresh, and it's the one thing a cold session can't recover.

Installed quality tools: see ENV_MAP (per-host).

Quality gate: `ck gate` runs the repo's detected checks; on `standard` the pre-commit hook warns on failure (non-blocking).

Architecture boundaries (opt-in): declare forbidden dir→dir imports in `.context-kit/boundaries` (e.g. `ui !-> db`, names match ARCH_MAP); a crossing edge then fails `ck gate`. Commit the file — it's shared policy, not local scratch.
