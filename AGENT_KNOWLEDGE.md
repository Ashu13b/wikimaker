# AGENT_KNOWLEDGE

Hand-written, agent-maintained. The maps say *what exists*; this says *why*.
None of it is auto-derivable — keep it current as you learn.

## Intent
Wikimaker researches a person, resolves identity from multiple sources, checks
Wikimedia status, and builds the output appropriate to that status. A person
does not need an existing Wikipedia article or Wikidata item to start research.
The intended outputs are a new AfC draft, improvements to an existing draft or
article, or a research dossier.

## Execution context
The React frontend and FastAPI API run as one local service on port 3890.
Research is initiated interactively by a human and persisted as JSON sessions.

## State
There is no database. `sessions/*.json` stores a `PersonProfile`, Wikimedia
status, and save timestamp. In-memory session dictionaries mirror loaded work.

## Decisions & rejected approaches
- Identity resolution must not depend on Wikipedia or Wikidata. General web,
  academic, institutional, and researcher-ID sources provide optional identity
  clues; the human-entered subject remains a valid starting point.
- Wikimedia lookup is a separate routing check: `clear` creates a new-article
  workspace, `draft` improves the existing draft, `exists` becomes article
  research, and `deleted` requires deletion review.
- Name-only Wikidata photo selection is unsafe for same-name people. Wikidata
  enrichment requires a confirmed QID.
- Authored publications establish identity and career facts but must remain
  distinct from independent secondary coverage used for notability assessment.

## Half-done / known-broken
- Existing-article mode currently disables duplicate draft generation and
  supports research, but does not yet compare collected claims against live
  article content or emit a structured edit proposal.
- Wikimedia status lookup is title-based and is not itself proof that a
  same-named page describes the intended subject.
- The worktree contains a substantial pre-existing uncommitted feature set;
  preserve it and avoid treating all current changes as one finished feature.
- UI screenshot verification requires a Playwright Chromium binary. Playwright
  is installed on the current host, but its expected browser executable is not;
  the production frontend build remains available for structural verification.
