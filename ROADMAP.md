# ROADMAP

## Shipped
- Initial local person-research workflow with source collection, claim review,
  session persistence, and English/Hindi wikitext generation.

- Source-grounded deterministic draft pipeline with explicit claim approval,
  evidence diagnostics, server-owned generation, persistence, and a regression
  fixture that produces the Dr. Prem Singh Yadav draft without CV citations.

- Retired the legacy LLM/stub draft path (wiki/wikitext.py, StubProvider._draft):
  all drafting now goes through the audited deterministic renderer, so no code
  path can emit unverified or invented biography text.

- Existing-article mode: deterministic claim↔live-article comparison and a
  structured edit proposal (covered vs candidate additions), surfaced as an
  "Article proposal" tab when an article exists.

- Draft review tooling: Wikipedia-accurate preview (parsoid), live link checking
  with manual verification, and an AfC-style QA linter (structural + citation
  rules) gating readiness; DraftPage exposes Preview / Links / QA / Raw tabs.

- Draft renderer polish: citation title cleaning, dmy date normalization,
  structured-slot infobox, known_for lead sentence, {{Authority control}} /
  {{DEFAULTSORT}} / categories.

- Research-breadth + trust fixes: Indian press domains added to the provenance
  trust map and classifier fast path (news18, bhaskar, etvbharat, kisantak,
  devdiscourse, ...), archive-url/archive-date citations derived from Wayback
  timestamps, and agent-loop lessons recorded (classifier JSON key, claim
  confirm/approve step) — the Yadav session now audited at 20 independent
  sources / 63 eligible claims.
- Playwright automation: `check_draft_links` adjudicates blocked/unknown links
  with a real page render in a throwaway tab (requests stays primary);
  `FetchResult.final_url` + `is_meaningful_redirect` auto-flag silent redirect
  traps (`Source.redirected_to`, "⇢ Redirect trap" badge);
  `POST /api/research/fetch-blocked` walks blocked sources through the remote
  browser, stopping only at a real CAPTCHA.
- Stable subject/session ids: sessions are keyed by an immutable `session_id`
  (`py-<slug>-<hex>`) instead of the display name; files live at
  `sessions/{session_id}.json`, legacy name-based files migrate on resume, and
  `_get_profile(name_or_id)` resolves by id then name (ambiguous same-name
  lookups raise 409). `research_start` resumes an existing same-identity session
  (same name AND matching/absent wikidata) instead of duplicating; same name
  with a different identity hint gets a fresh id. Frontend passes the id via
  `profileRef(profile)`.
- Subject-first onboarding: `POST /identify` surfaces confirmable
  Wikipedia/Wikidata identity candidates (`find_candidates`, previously dead)
  with stable ids, ahead of generic web clues; research_start routes by a
  confirmed `wikipedia_url` (handles parenthetical disambiguators).
- Claim-level provenance separation: audit warning
  (`achievement_claim_not_independent`) for known_for/award claims resting only
  on non-independent sources; claims UI badges verified_independent /
  primary_sourced / unverified; evaluate_claim_trust never marks authored works
  verified_independent.
- Review fixes: resume re-checks Wikimedia status (stale status no longer
  trusted); bot-wall vocabulary single-sourced (`engine.fetcher.BOT_WALL_RE`);
  `delete_session` no longer evicts same-named namesakes; Semantic Scholar
  notability signals TTL-cached (was hammering the API on every save); the
  browser-server fetch path probes the unified `/browser` mount (7070 constant
  was dead).
- Modularity: `backend/routes.py` split into routes_research / routes_draft /
  routes_sessions; `browser_server.py` HTML extracted to `browser_ui.html`
  (744→390 lines); `store._lock` serializes session saves.
- Checker/verifier separation: `wiki/draft.py` is audit+generation only;
  `wiki/draft_verifier.py` owns link extraction/liveness + preview render;
  `wiki/draft_qa.py` is the static checker; `POST /draft/verify` runs both and
  returns `{qa, links, verified}` (live: verified=true, QA 0/0/1, 42/42 links).
- UI polish: generate-draft consolidated to header CTA + pipeline step (was 4
  buttons), disabled CTA shows the blocker reason; claim "include in draft"
  constrained to usable sources; resumed-session banner; ResearchPage fake
  step-timer removed; DraftPreview duplicate destination link removed;
  cancel added to the research spinner.

- Claim-aware notability coverage: count distinct independent outlets only when
- Dual research/AfC workflow: source-level coverage depth, editorial-origin
  grouping for syndicated reports, and durable research notes are persisted in
  sessions. Notability counts only human-assessed significant origins; a
  deterministic Markdown dossier exports all evidence while the wikitext
  renderer remains limited to confirmed, explicitly draft-approved claims.

  they support a confirmed claim; raw source/publication counts and unvalidated
  name-only citation metrics no longer produce an AfC acceptance prediction.

- Unified publisher registry (`engine/publishers.py`): Consolidated independent
  news, academic journals, institutional/primary, self-published, and unreliable
  domains into a single authoritative source of truth, removing ad-hoc domain
  lists across classifier, provenance, and draft engines.
- Structured editorial draft paraphrase controls (`Claim.draft_text`): UI allows
  customizing exact Wikipedia draft phrasing without mutating the underlying
  historical verbatim claim extracted from the source (`edit_draft_text`).
- Direct 1-click AfC submission helper: `Copy for AfC (with {{subst:submit}})` in
  `DraftPage.tsx` prepends submission template for direct Wikipedia submission.
- Complete documentation & quality conventions: `README.md` authoring, house style
  conventions in `.context-kit/conventions`, and test suite purposing.

## Next
- Second-subject dry run: Dr. Vishwa Mohan Katoch (V. M. Katoch, India) —
  exercises identify → verify → review → draft on a fresh identity instead of
  the Yadav fixture.
- Expand automated coverage for identity conflicts, source verification, and
  session migration.
- Add multi-language draft translation assistance (e.g. Hi-Wiki support) with
  matching Hindi citation templates.

## Out of scope
- Requiring a pre-existing Wikipedia article or Wikidata item before research.
- Automatically generating a competing draft when an article already exists.
