<!-- context-kit managed · >>> context-kit >>> <<< context-kit <<< -->
# AGENTS.md

Single source of truth for every agent in this repo. `CLAUDE.md`, `GEMINI.md`,
etc. just point here.

## 0. Always-loaded indexes
@CODE_MAP.md
@ARCH_MAP.md
@DEPS_MAP.md
@DOCS_MAP.md
@WORKFLOW.md
@ENV_MAP.md

`WORKFLOW` is the development protocol for this repo's rigor profile — follow it.
`DOCS_MAP` indexes existing docs by heading — load the full doc on demand.
`AGENT_KNOWLEDGE.md` holds intent/state/context — read it when the *why* matters.
`ROADMAP.md` holds shipped/next/out-of-scope — read it before proposing new work.

## 1. Discovery protocol (do this, not habit)
- Consult **CODE_MAP** for symbol/file location before Grep/Read. On a large repo
  it renders as a *router* (a line-budgeted subset of files); when the banner says
  router mode, find a symbol with `.context-kit/ck where <name>` and read a file's
  symbols with `.context-kit/ck show <path>` instead of assuming it lists everything.
- Consult **ARCH_MAP** before adding a cross-directory import — it shows the dir→dir
  dependency edges and flags cycles; write within the existing seams.
- Consult **DEPS_MAP** before assuming a package or env key exists.
- Consult **ENV_MAP** before assuming the runtime (OS, versions, this host).
- If the SessionStart banner says maps are stale, run `.context-kit/ck build`.

## 2. What this project is
Wikimaker is a local research workspace for resolving a person's identity,
collecting and verifying sources, checking Wikimedia status, and producing the
appropriate output: a new AfC draft, improvements to existing content, or a
research dossier.

## 3. Commands
- Rebuild maps: `.context-kit/ck build`
- Check staleness: `.context-kit/ck check`


## 4. Non-obvious rules
See `AGENT_KNOWLEDGE.md`. Keep it current — when you learn *why* something is
the way it is, or what was tried and rejected, write it there.

## 5. Development protocol
See @WORKFLOW.md — the loop is profiled (`light`/`standard`/`strict`). Don't
refactor opportunistically. Verify via the actual CLI/UI when possible.
