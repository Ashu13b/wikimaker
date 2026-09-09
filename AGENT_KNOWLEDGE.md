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

- Drafting is server-owned and deterministic. The browser identifies a session; it
  does not submit an editable PersonProfile as draft input. Generated wikitext is
  persisted back to that session.
- Claim verification and editorial draft approval are separate decisions. Only
  confirmed or edited claims explicitly approved for drafting can enter wikitext,
  and editing or skipping a claim revokes that approval.
- Private CVs and local files are research leads only. They may guide searches but
  are never eligible citations or direct draft evidence.
- A source count cannot prove academic notability. Independent project coverage,
  authored publications, institutional profiles, and awards remain distinct; the
  final WP:ACADEMIC/GNG judgment must be made by a human.
- Katoch dry-run lesson (Aug 2026): field intuition is NOT a wrong-person test.
  The S2 author id `2147684` looked contaminated (yoga/CVD/API-economics papers
  for a leprosy microbiologist) but `check_doi_authors` confirmed every paper —
  they are his late-career ICMR/RUHS collaborations. Always adjudicate
  namesake suspicion with the CrossRef authorship checker, not by topic match.
- Auto-research accuracy hardening (same pass): `_pick_author_id` no longer
  falls back to highest-paper-count when CrossRef validates nothing (that
  fallback was the recorded contamination vector; it now returns None).
  Source-URL-extracted semantic_scholar ids are gated by
  `validate_s2_author` (first+last name token check, fail-closed). A junk URL
  filter (`is_junk_source_url`) drops e-paper image renders (tribuneindia
  sortd-service) and bare image assets from auto-sweeps. scispace.com,
  scilit.net, gpatindia.com added to UNRELIABLE_DOMAINS.
- Researcher-ID ingestion is gated: `validated_new_ids` (engine/researcher_ids.py)
  drops source-URL-extracted ORCIDs that fail identity validation before they
  enter `profile.researcher_ids` (all three ingestion points: initial sources,
  add-source, resume re-extract). Only NEW ids are gated — stored ids are never
  re-validated on resume because `validate_orcid` returns False on any network
  exception, so offline resume would otherwise silently drop valid ORCIDs.
  Stored-but-wrong ids are pruned by the find-ids endpoint instead. Google
  Scholar/Scopus/ResearchGate have no deterministic validator and stay
  human-confirmable via `confirmed_ids`.
- The Prem Singh Yadav CV audit increased the saved session from 45 to 70 public
  sources and the deterministic draft from 10 to 28 eligible claims tied to 26
  sources. Seven distinct independent outlets support included claims. The
  strongest plausible WP:ACADEMIC argument is criterion 2: the official ICAR
  citation names Yadav as team leader for the nationwide, externally judged
  Nanaji Deshmukh award in Animal and Fisheries Sciences; 12 eligible
  applications competed for two disciplinary awards. Business Standard and
  Amar Ujala independently discuss his cloning-programme role and applied
  breeding significance. This is a stronger but still reviewer-dependent
  notability case, not a guarantee of acceptance. The pass also verified the
  2025 retirement, 1993 joining date, 2003–04 DBT overseas associateship,
  DAAD-backed 2010–11 German research stay, and India and Limca record
  recognitions. NADS remains excluded because no official roster or reliable
  independent source located so far names Yadav.
- Distinct domains are not necessarily distinct editorial origins: Deccan Herald,
  NDTV, and other Sach-Gaurav pages syndicate the same wire account, so mirrors
  are corroboration rather than extra notability evidence. Citation aggregators
  also require identity auditing. The DOI-resolved OpenAlex identity is
  `A5111039070` (matched through the verified Nature and PLOS papers and CIRB
  affiliation/email), but it contains two obvious namesake works; Semantic
  Scholar is split and contaminated. A saved Google Scholar ID belonged to an
  Oregon State namesake, ORCID `0000-0003-0982-9408` belonged to Sheetal Saini,
  and another stored ORCID returned 404. The false identifiers were removed,
  and citation totals remain research leads rather than draft facts.
- Earlier generated drafts are research leads, not evidence. Recheck every URL:
  the Yadav drafts mixed a valid NDTV/PTI lead with fabricated placeholder URLs,
  invented ICAR paths, and an incorrect Nature article identifier. The Nature/
  Scientific Reports article is real; its canonical identifier is
  `s41598-019-47909-8`.
- The legacy LLM draft path (wiki/wikitext.py render_en/render_hi, generate_draft.py,
  StubProvider._draft) was retired. With no API key it silently emitted hard-coded
  biography prose and invented citations (e.g. "100% verified" source directories
  full of dead URLs), which is why the visible deliverables failed the project goal.
  Drafting is now deterministic only: generate_draft.py and POST /api/draft both
  call wiki.draft.render_draft, and the stub provider raises if a draft prompt
  reaches it. Regenerated wikitext_draft_prem_singh_yadav.md from the audited
  session evidence (27 sources, 29 eligible claims, 7 independent outlets).
- The draft audit now hard-blocks on fewer than two independent secondary outlets
  (code `insufficient_independent_coverage`); a draft of purely institutional or
  primary sources is no longer "ready". Independence is decided by the expanded
  `_INDEPENDENT_NEWS_DOMAINS` list OR provenance classification
  (`is_independent` + `independent_secondary` + `reliable_secondary`).
- Discovery was widened: fetch_auto_sources now also runs a national-outlet
  site-restricted sweep (`_sweep_news` in engine/researcher.py) including a Hindi
  query, and the suggester appends `site:<outlet>` safety-net queries for
  high-value slots. Auto-enrich covers the top 5 missing slots instead of 3.
- Hisar Gaurav 2.0 (a new clone of the same donor bull, born 28 Nov 2025 and
  unveiled 18 Dec 2025, covered by Jagran/Amar Ujala/vartahr) was considered and
  deliberately NOT added: Yadav superannuated in April 2025 and the reports do
  not attribute the new clone to him, so including it risked implied
  attribution. Post-tenure institute milestones stay out of the biography even
  when they extend the subject's research lineage.
- `check_draft_links` treats `doi.org/` URLs that return 401/403/429 as ok: the
  resolver redirect succeeding means the DOI is registered, and publishers'
  bot-walls are not link death. This mirrors the archive.org 498 handling. The
  live draft's only "blocked" links were DOI publisher pages, not real breakage.
- Link liveness via Playwright's `APIRequestContext` (`ctx.request`) is a WORSE
  bot fingerprint than plain `requests` with the project's Chrome UA: it sends
  the HeadlessChrome UA and page init-scripts (stealth) don't run on request
  contexts, so sites like Moneycontrol/PubMed/Bhaskar that serve `requests` 200
  return 403 to it. Playwright's genuine value is the page-render adjudicator
  (`link_status_page`): a throwaway tab with stealth + JS that re-checks only
  the blocked/unknown leftovers, using the warmed companion profile (cookies +
  history) so it behaves like a human browser. `check_draft_links` keeps plain
  requests primary and never force-starts the browser for a link check. The
  companion context now launches with a desktop Chrome UA (`browser_server._UA`).
- Silent redirect traps are now auto-caught: `FetchResult.final_url` records the
  page's real URL after redirects (direct fetch via `resp.url`, browser path via
  the page URL), and `is_meaningful_redirect` (engine/relevance.py) flags a
  source `uncertain` + records `Source.redirected_to` when a URL lands on a
  materially different page. It ignores scheme/www normalisation, AMP variants,
  query params, URL shorteners (trib.al etc.), and DOI resolvers. The jagran
  trap (URL served an unrelated 2015 article) is exactly the pattern it catches;
  rechecking the same jagran URL later showed the site now serves the right
  page, so traps can be transient. Verdict is deliberately `uncertain`, not
  `likely_wrong`, to avoid hard-excluding a source on a slug-normalisation false
  positive; the human/LLM classifier decides from `redirected_to`.
- `POST /api/research/fetch-blocked` auto-walks sources with `liveness ==
  "blocked"` through the remote browser: navigate → capture rendered text →
  wall-check (`browser_server.looks_like_wall` reuses `_WALL_SIGNALS`) → update
  the source in place (snippet, liveness=alive, fetched_by=browser) + classify/
  flag/check_doi, then recompute notability. Stops at the first real bot wall so
  the human solves it in the companion browser, then resumes. The UI shows an
  "Auto-fetch blocked" button only when blocked sources exist; `fetched_by`
  gained the `browser` value in the SourceFetchedBy union. This is the research
  phase counterpart to the link-check adjudicator: Playwright does navigation
  and capture, a genuine CAPTCHA is the only thing that pauses.
- Sessions are keyed by an immutable `session_id` (`py-<slug>-<8hex>`,
  `store._new_session_id`), not the display name. `_sessions`/`_wiki_statuses`
  and files (`sessions/{session_id}.json`) are id-keyed; `store._get_profile`
  resolves by id first then by name, raising 409 on an ambiguous same-name
  match. Legacy name-based files migrate on resume/start (old file unlinked).
  `research_start` collision policy: same display name AND (wikidata equal or
  both absent) → resume the existing session (`resumed: true`); same name with
  a different identity hint → fresh id, so same-named people never clobber.
  The frontend passes the id everywhere via `profileRef(profile)`
  (`session_id ?? name`) so a session is addressable even after a rename.
  `tests/conftest.py` has an autouse fixture redirecting `SESSIONS_DIR` to a
  tmp dir — without it, id-keyed saves litter the real sessions dir on every
  test run (each save is a new unique filename).
- Claim-level provenance separation: `claim.provenance_status` /
  `claim.is_independent` were computed but never consumed. The draft audit now
  emits an `achievement_claim_not_independent` warning when known_for/award
  claims in evidence rest only on non-independent sources (institutional/
  registry pages) — warning only, never an eligibility change, so the QA
  counts stay 0/0. The live Yadav audit flags 7 such achievement claims (all on
  cirb.res.in / icar.gov.in / icar.org.in / indiabookofrecords.in). The claims
  review UI already badges verified_independent / primary_sourced / unverified
  (ClaimsReview.tsx), and `evaluate_claim_trust` already classifies authored
  publications as primary_sourced, never verified_independent.
- Subject-first onboarding: `POST /identify` now merges Wikipedia/Wikidata
  identity candidates (`engine.identifier.find_candidates`, previously dead
  code) tagged `kind: "identity"` ahead of generic web clues. The user can
  "Confirm this person" to carry `wikidata_id`/`wikipedia_url`/photo into
  research_start. Confirming keeps the user's typed name (not the article
  title); routing precision comes from research_start deriving the wiki-check
  title from a confirmed `wikipedia_url` (handles parenthetical disambiguators
  like "Prem Singh Yadav (scientist)"). This is also the safe photo path: the
  legacy name-based `fetch_wikidata_photo` (documented footgun) was deleted.
  The identity section renders only when a real match exists — it degrades
  gracefully to web clues alone.
- Cleanup: deleted dead `frontend/src/components/CandidateCard.tsx`, the unused
  `addSourcedClaim` api wrapper, unused `engine.fetcher.fetch_orcid_by_name` /
  `fetch_text_paste`, and `engine.identifier.fetch_wikidata_photo`;
  simplified `DELETE /sessions/{ref}`; `identify` web-search is wrapped so a
  provider hiccup can't 500 the preview.
- Review fixes: `DELETE /sessions/{ref}` used to evict EVERY in-memory session
  sharing the person's display name (deleting one same-named person dropped its
  namesake from memory too) — removed the stale name-keyed eviction. The
  redirect detector false-flagged mobile/amp subdomain redirects (`m.`/`amp.` →
  www) as traps; `_redirect_norm` now strips `m.`/`mobile.`/`amp.`/`www.`.
  `_apply_provenance` recomputed notability on every save, which fired a
  Semantic Scholar API call each time (rate-limited ~100/5min); notability now
  TTL-caches S2 signals per name (10 min). The browser-server fetch path was
  dead in the unified layout: `engine.fetcher._try_browser_server` pointed at
  `localhost:7070` (the retired standalone port) while the browser is mounted
  at `/browser` on 3890, so the companion-browser fetch silently never ran — it
  now probes 3890/browser then 7070, and `store.BROWSER_SERVER` (unused) was
  deleted.
- Resume now re-checks Wikimedia status (via `wiki.wiki_check.check_title_for`,
  which derives the article title from a confirmed `wikipedia_url`) instead of
  trusting the stored `wiki_status`, so a session resumed after an article was
  created routes to `exists`/`draft` correctly. The check is wrapped in
  try/except so an offline resume keeps the stored status. Resume tests patch
  `wiki.wiki_check.check_existing_page` to stay offline-deterministic.
- Concurrency: `store._lock` (threading.RLock) serializes `_save_session`
  (apply-provenance + snapshot to disk), `_resolve_profile`, and
  `_activate_session`; routes mutate the shared in-memory profile (GIL-atomic)
  then snapshot under the lock. research_start's fresh-path keying also runs
  under `store._lock`. Fine-grained enough for the threadpool without locking
  every route.
- Routes were split for modularity: `backend/routes.py` (894L) became
  `backend/routes_research.py` (research/source/claim handlers + research_router),
  `backend/routes_draft.py` (draft audit/generate/links/preview/qa + draft_router),
  and the session handlers moved into `backend/routes_sessions.py`.
  `main.py` includes all three routers and still re-exports every public handler
  name for tests/frontend.   `browser_server.py` dropped 744→390 lines by moving
  its embedded companion-browser HTML to `browser_ui.html` (loaded via
  `_browser_html()`). Test monkeypatch targets moved from `backend.routes.` to
  `backend.routes_research.`.
- Checker/verifier split after generation: `wiki/draft.py` now contains only
  audit + generation. `wiki/draft_verifier.py` holds `extract_draft_links`,
  `check_draft_links`, `_check_links_via_requests`, `render_preview`, and
  `DraftLink` (moved out of draft.py, which also dropped a dead `_BARE_URL`
  regex). The checker stays `wiki/draft_qa.py` (static lint). New
  `POST /draft/verify` runs checker + verifier and returns `{qa, links,
  verified}`; the DraftPage tabs are labeled "Verify · links live" and
  "Check · AfC lint". Live run: QA 0/0/1, 42/42 links ok, `verified: true` —
  one citation (ndri.res.in PDF, host unreachable) needed a Wayback
  archive-url (20251028060629) to pass the verifier.
- `POST /identify` now also returns `wiki_status`: the Wikimedia routing
  outcome (clear/draft/exists/deleted) shown on the onboarding confirm screen
  before research starts, so the user knows they're entering new-article vs
  existing-article/draft mode. The check prefers the top identity match's
  `wikipedia_url` title (via `check_title_for`) when one is offered. The
  identify test mocks `wiki.wiki_check.check_existing_page` to stay offline.
- Bot-wall vocabulary is now single-sourced: `engine.fetcher.BOT_WALL_RE`
  (regex) is shared by the headless fetcher (`fetcher_browser`) and the remote
  browser's `looks_like_wall`/link adjudicator — the two signal lists used to
  drift apart. `fetchable` is a UrlSuggestion-only field (Source has no such
  column), so `fetch_blocked` correctly keys on `liveness == "blocked"` and
  never re-walks DOI/pipeline sources.
  get_provider() prints a loud one-time warning when it silently falls back to
  StubProvider.
- The Yadav draft regression test now reads a frozen fixture
  (tests/fixtures/Prem_Singh_Yadav.json) instead of the live session file, so
  session growth no longer breaks it.
- resume_session never repopulates claims from the stub provider
  (has_real_llm guard) — stub-extracted claims are fabricated and would
  silently pollute an otherwise clean session.
- Live session research round (Yadav draft): expanded the draft ~18.6k → 20.1k
  chars by adding independently-sourced applied-breeding facts. Key lesson —
  PTI wires are syndicated: the etvbharat English "Hisar Gaurav turns 7"
  article and statetimes.in are the SAME story (one editorial source), so only
  one is citable for independence. Added via add-sourced-claim + approve_draft:
  14,000 semen doses to Nuh farmers (etvbharat, independent), 950 kg fit at
  age 7 (etvbharat, independent), commercial breeding viability field trials
  (Tribune, independent), frozen-semen AI protocols (Tribune, independent),
  GenBank male-fertility variants KU364415/6, KX463461/2, and piggyBac iPSC
  reprogramming (CIRB AR 2016-17, primary).
- Two gotchas from that round: (1) `research_claim_has_no_subject_action`
  matches `"co-discoverer"` but not `"co-discovered"` — action-verb prose must
  use an allowed token verbatim; (2) direct edits to the session JSON on disk
  are CLOBBERED by the next `_save_session` if the running server still holds
  the old in-memory profile — after editing the file, resume first, then call
  save-paths (verify/generate) with no other mutating API call in between, or
  the disk edits are lost.
- The `research_claim_has_no_subject_action` rule's action-word list was too
  narrow and silently dropped real research facts ("found", "described",
  "co-discovered", "weighed", "was in demand" all failed it). Widened to
  `_RESEARCH_ACTIONS` (extracted constant) with common research verbs
  (found/described/demonstrated/showed/studied/assessed/evaluated/weighed/
  compared/identified/noted/co-discover). Also fixed the renderer's Research
  section silently truncating approved `known_for` claims at a hard cap of 12 —
  raised to 20 so approved facts always render (a hidden cap that drops
  approved content is   data loss, not editorial control).
- Subject/animal conflation hardening: the birth-noise rule previously scanned
  only the claim text, so a clean-text birth claim ("Born on December 11, 2015")
  sourced to a cloned-calf article would slip into the person's birth_date. It
  now also scans the source title (birth_context = text + source.title), so any
  birth_date/birth_place claim whose claim OR source mentions calf/buffalo/bull/
  cow/animal/clone/kg/delivery is excluded as `claim_appears_to_describe_animal`.
  Live session: a "4 kg born through normal delivery" calf fact was extracted
  into birth_date and is double-blocked (unapproved + noise rule). The 270 kg /
  first-birthday milestone is the BULL Hisar-Gaurav, not Dr Prem; his birth
  (10 April 1963, staff list) renders separately and correctly.
- The suggester's multi-year URL sweep was fabricating DOIs: it replaced the
  year inside any URL containing one, turning `doi.org/10.48165/aru.2023.3.1.6`
  into fake `...2000...` DOIs. `_generate_multiyear_report_urls` now refuses
  publisher/academic hosts and only sweeps institutional report URLs
  (cirb.res.in etc.). Site-restricted news results are ranked above those
  unverified report guesses.
- Dogfood run on the live Prem Singh Yadav session (no real LLM on this host)
  drove real fixes:
  - `get_provider()` now uses Vertex AI Claude when `ANTHROPIC_VERTEX_PROJECT_ID`
    is set (the host's intended auth via gcloud ADC) instead of falling straight
    to the stub; a construction-time probe means projects without model access
    still fall back cleanly (verified here: model 404 → stub).
  - `extract_claims()` is a no-op under Stub/Null/Local providers — the stub
    fabricates plausible claim prose ("Dainik Jagran national coverage on Dr"),
    so no new junk claims are ever injected; humans add facts via add-document-fact.
  - `targeted-search` and `auto-enrich` drop `self_published`/`unreliable`
    sources before adding, so a search can no longer flood the session with
    LinkedIn dir pages, personal trainers, or wrong-person profiles.
  - The multi-year report guesses are bounded to `max_results - 2` so real
    search results always get queue slots.
  - Session cleanup: rejected the stub-era fabricated HT placeholder
    (`story-123456789.html`, now 410), a wrong-person ju.edu.et staff page, 10
    self-published (LinkedIn/urbanpro/twitter) and 9 wrong-person/noise sources.
    Session is now 79 sources, 134 claims, 68 verified, audit ready with 25
    evidence sources / 27 eligible claims / 8 independent outlets (after the
    live evidence audit removed two unsupported claims, below).
- Live evidence audit (Aug 2026): re-fetched every evidence URL and compared it
  against the claims it supports. This caught two approved claims whose cited
  sources did not back them:
  - The education claim (B.Sc. 1985 / M.Sc. 1987 / Ph.D. 1991, CCSHAU) cited the
    bagchee.com book page, which is a JS-rendered SPA whose server HTML and
    Wayback snapshot contain no such bio; the facts actually trace to the private
    CV, which is ineligible draft evidence. Removed from the draft.
  - The "CIRB 2022 annual report recognised cloning work by the Limca Book of
    Records" claim: the AR 2022 PDF never mentions Limca/Book of Records.
    Removed from the draft.
  - Verified-supported: the ICAR Partnership PDF does name "P S Yadav ... DBT
    Overseas Associateship (long-term) award, 2002-03 ... w e f 15 November 2003"
    (OCR garbles Neustadt as Neustedt); the 2023 staff list shows 04/10/1963 birth
    and 04/12/1993 joining (MM/DD, so 10 April 1963 / 12 April 1993); the ICAR
    Award 2019 citation on page 157 names "DR. P. S. YADAV (Team Leader)" for the
    Nanaji Deshmukh award in Animal & Fisheries Sciences; the AR 2010-11 records
    "Research stay and study Farm Animal Genetics, Germany, PS Yadav
    December 28-10 February, 2011"; and CrossRef confirms Prem Singh Yadav as a
    co-author on all four DOI publications. The draft now has 25 evidence
    sources / 27 eligible claims / 8 independent outlets and no Education section
    (no verifiable public source).
- Lesson: claim approval trusts the LLM extraction + human click; neither re-reads
  the source. A draft can therefore carry a claim whose cited page does not
  actually contain it. The audit cannot cheaply auto-verify claim↔source content
  (OCR garbles names/dates and bot-protected pages block plain fetches), so this
  stays a human-review responsibility. Notable app gap: there is no endpoint to
  add a *sourced* claim manually (add-document-fact is timeline-only and
  unsourced), so in stub/no-LLM mode a user who reads a verifiable fact (e.g. the
  staff-list birth date) cannot enter it bound to its source.
- Added `POST /api/research/add-sourced-claim` (+ frontend `addSourcedClaim`) so a
  human who reads a fact in a source can bind it to that URL. The source must
  already be in the session; the claim is created confirmed/user-provided and
  still requires an explicit approve-for-draft action. This closes the gap above
  and is what stub/no-LLM workflows need.
- CV-to-public-source dig (the CV is truthful but not citable; each fact must get
  a real link): the 2023 CIRB staff list confirms birth 10 April 1963 and joining
  12 April 1993 (`04/10/1963`, `04/12/1993` in MM/DD); the publisher's page for
  his book (satishserial.com, HTTP 200, author bio read verbatim) confirms the
  education (College of Agriculture HAU 1985; M.Sc. 1987 and Ph.D. 1991 from
  CCSHAU) and the career trajectory (Scientist 1993, Senior Scientist 2000,
  Principal Scientist 2008); the archived official CIRB profile confirms M.Sc./
  Ph.D. and "Principal Scientist and Head, APR Division". These four claims were
  added and approved. The NADS (dairyacademy.org) fellowship remains unsourced —
  no reachable official roster names Yadav; it stays out of the draft. Session is
  now 79 sources / 138 claims, audit ready with 26 evidence sources / 31 eligible
  claims / 8 independent outlets.
- International/German facts, all citable and verified first-hand: the DBT Overseas
  Associateship (12 months, w.e.f. 15 November 2003, Neustadt) from the ICAR
  Partnership PDF; the DAAD research stay at Farm Animal Genetics, Germany, Dec
  2010-Feb 2011 from the AR 2010-11; and a career claim tying the 2005 paper
  "Bovine ICM derived cells express the Oct4 ortholog" to the Institute for Animal
  Breeding (FAL), Mariensee, Germany and Heiner Niemann's group — Europe PMC gives
  that exact affiliation and CrossRef confirms the authors (Yadav, Kues, Herrmann,
  Carnwath, Niemann; DOI 10.1002/mrd.20343, Molecular Reproduction and Development
  2005). This also caught and fixed a claim error: the 2005 paper was mislabeled
  "Cellular Reprogramming" and is actually Molecular Reproduction and Development.
  The Royan (Iran) jury membership and a China expert visit from the CV have no
  reachable verifiable public source, so they stay out of the draft. Session is now
  26 evidence sources / 32 eligible claims / 8 independent outlets.
- Checked four user-supplied share.google links: two resolve to sources already in
  the session (CIRB AR 2016-17; IntechOpen profile 289144), one is a dead link
  (share.google/error), and the Google Books "Telomerase" link turned out to be the
  IntechOpen chapter already in the session (chapters/70617). CrossRef confirms
  that chapter: DOI 10.5772/intechopen.89506, "Telomerase Structure and Function,
  Activity and Its Regulation with Emerging Methods of Measurement in Eukaryotes",
  in Telomerase and non-Telomerase Mechanisms of Telomere Maintenance (IntechOpen,
  2020), authors Prem Singh Yadav & Abubakar Muhammad Wakil. Its session claims were
  stub junk ("Prem Singh Yadav *", "Author details..."); replaced with a proper,
  draft-approved publication claim and the junk claims skipped. Session is now 27
  evidence sources / 33 eligible claims / 8 independent outlets. None of the four
  links evidence the claimed 2025 Varanasi cloning-conference award, which remains
  unverified.
- Varanasi award located and verified. The user's recollection ("world cloning
  conference, Banaras, ~19-22 Feb 2026") is the Global Summit on Innovations in
  Reproductive Biology: Emerging Frontiers and Discoveries — the 36th annual
  meeting of ISSRF (Indian Society for the Study of Reproduction & Fertility),
  20-22 February 2026 at Banaras Hindu University, Varanasi. The official BHU
  program schedule (bhu.ac.in/Images/files/Scientific Program Schedule
  GSIRB-ISSRF 2026.pdf) lists "Prof. S. S. Guraya Memorial Oration — Dr. P. S.
  Yadav, ICAR-CIRB, Hisar — Technological advances in buffalo cloning: From
  embryo optimization to field-level validation". A memorial oration is an invited
  named honor; added as a sourced, approved award claim citing the BHU PDF, and
  the source was added to the session. Official dates are 20-22 Feb (not 19-22).
  Session is now 28 evidence sources / 34 eligible claims / 9 independent outlets.
- News sweep on Hisar Gaurav and the cloning record found two more verifiable
  official sources, both added with sourced claims: the CIRB news release of 30
  July 2020 ("commendable achievement... producing seven clones from a single
  breeding bull M-29 and a re-cloned calf of Hisar-Gaurav, born October 2019 to
  January 2020", naming PS Yadav first among the team; announced at ICAR's 92nd
  Foundation Day, 16 July 2020) and ICAR news node 12458 (names Yadav as principal
  investigator of the NASF-funded buffalo cloning project). Bot-blocked but
  plausible new outlets (businessworld, zeenews, india.com) could not be verified
  first-hand and were not added. Limca: the citable source stays the Amar Ujala
  article (15 March 2023) reporting CIRB's name entered in the Limca Book for
  "maximum clone for one bull"; per the user, LBR 2023 (Hachette India) was
  released 25 December 2022, consistent with the March 2023 report. No separate
  online page lists the LBR entry, so no stronger source exists. Session is now 30
  evidence sources / 36 eligible claims / 9 independent outlets.
- Further dig found two more claimable sources (verified first-hand, both added):
  dharmakshethra.com (independent news naming "Prem Singh Yadav from CIRB" for the
  PLOS ONE cloned-bull study) and the official CIRB news "ICAR-CIRB celebrates first
  birthday of cloned calf, Hisar-Gaurav" (names "team leader Dr. Yadav", 270 kg at
  one year). Bot-blocked outlets (BusinessWorld, Zee, India.com, HT Sach-Gaurav 404,
  Financial Express 403) could not be verified and Wayback was unreachable, so they
  stayed out. The Research section's 6-item cap was dropping the 2020 seven-clones
  record and Business Standard 2021; the render limit in wiki/draft.py was raised
  6 -> 10 so all verified research coverage renders. Session is now 32 evidence
  sources / 38 eligible claims / 9 independent outlets.
- "Claim the sources" pass: all 74 session sources were already verified (the user's
  premise of unverified sources was already resolved by cleanup). The 9 verified but
  claim-less sources were read first-hand: Deccan Herald (JS-shell, no content) and
  TOI cloned-cow (bot-blocked, and about NDRI's cow not CIRB) yielded nothing; the
  NASF Glimpses PDF has no Yadav name; the CIRB Annual Report 2020 corroborates the
  seven-clones + re-clone record (already claimed via CIRB news) and cites
  "Yadav et al., 2020, Current Science 119(7):1077". CrossRef resolved the related
  Sach-Gaurav paper: DOI 10.18520/cs/v115/i2/198-198, "Sach-Gaurav: World's First
  Cloned Buffalo Born In The Field At An Indian Dairy Farm", Current Science 115
  (2018), authors Selokar, Sharma, Kumar, Sharma, P. S. Yadav — added as a draft
  publication claim. Publication render cap raised 8 -> 10 so it renders alongside
  the 2005 MRD paper. Session is now 33 evidence sources / 39 eligible claims /
  9 independent outlets.
- UI clarity for the verify→suggest→approve flow (frontend): auto-extracted claims
  now carry an "AI-suggested · review" chip (vs "manual entry" for user-entered or
  add-sourced-claim facts); the SourceCard's inline claim block is retitled
  "Suggested claims (N)" with per-claim verification state and the explicit note
  that verifying a source does NOT put claims in the draft (confirm/edit in the
  Claims tab, then press +). The verify button reads "✓ Verified · N claims
  suggested". This makes the three-step model (source verified → claims suggested →
  human-approved) visible instead of implied.
- Leftover-source cleanup: all 10 unverified session sources were triaged. 9 were
  rejected as wrong-person/irrelevant/dead (core.ac.uk PDF 404, an openthe/ndtv/
  clarion/indianexpress cow-transport & politics noise, bookbrowse reader reviews,
  a Hindi Wikipedia university page, a Manmohan Singh GK page, an RG contributions
  page). The one real find — acspublisher.com ARU article view/1114 (Animal
  Reproduction Update, DOI 10.48165/aru.2021.1204, "Prem Singh Yadav, Embryo
  Biotechnology Laboratory, ICAR-CIRB, Hisar") — was verified and kept as a session
  source but given no draft claim so it cannot displace a stronger publication.
  Session is now 72 sources, all human-verified, 30 evidence sources / 36 eligible
  claims / 9 independent outlets. The only remaining human task is the final
  AfC review of the rendered wikitext.
- Agent-as-LLM fallback is the default when no API key exists. `get_provider()`
  fallback order is now: real LLM API (Claude/Gemini, or Vertex) → **coding agent**
  (`AgentProvider`) → deterministic code. The stub is only used with the explicit
  `WIKIMAKER_LLM=stub`. `engine/agent_llm.py` queues each extraction/classification
  prompt as a deterministic JSON job in `agent_jobs/` (keyed by prompt hash); an
  unanswered job returns `{}` (never fabricated), and the coding agent answers it by
  reading the source and writing a `.response.json`, after which a re-run returns
  the answer. Helpers: `pending_jobs()` lists unanswered jobs, `answer_job()` writes
  a response. This was demonstrated live: extract_claims on the ARU "Impact of High
  Temperature on Oocytes and Embryos" review queued a job, the agent answered it,
  and the claim entered the draft. Session is now 38 evidence sources / 45 eligible
  claims / 11 independent outlets (incl. the agent-extracted ARU publication, the
  Veer-Gaurav source found by the liveness-gated sweep, and two closed CV gaps).
- CV-gap closure: two more gaps sourced and added. (1) The Indian Society for
  Buffalo Development conferred the Distinguished Scientist Award on Yadav at its
  National Conference, 17-19 Jan 2019, Navsari Agricultural University — CIRB news
  "national-conference-of-the-society" (award claim). (2) Birth place: the Amar
  Ujala Rewari retirement article states he is "resident of Village Nimoth"
  (गांव निमोठ निवासी) — birth_place claim. Still unsourced: NADS fellowship
  (dairyacademy.org down, no roster), ISSAR Outstanding Young Scientist 1996-97
  (too old).
- Liveness + Wayback fallback implemented (the "dead links" fix). `Source` gained  `liveness` (alive|blocked|dead|unknown) and `archive_url`. `engine/fetcher.py`
  `check_liveness()` GETs a URL with a browser UA: 404/410 -> dead (and looks up a
  Wayback snapshot via archive.org/wayback/available), 401/403/429 -> blocked
  (bot-protection; citable by a human, not dead), 2xx/3xx -> alive, 5xx/conn-error
  -> unknown. The audit excludes a claim whose source is dead *and* unarchived
  (`source_url_dead`), and the renderer cites `archive_url` (with an
  `archive-url=` field) when a dead source is archived. Wired at add-source
  (liveness from the fetch result), verify-source (definitive check at human
  confirmation), and via `_annotate_liveness` on discovery endpoints. A sweep of
  the 35 evidence sources found ZERO dead: 26 alive, 8 blocked (Cloudflare),
  1 archive URL. 403 != dead — blocked pages stay citable, which is why the
  user's browser (and the phone loop) are the fallback for blocked pages.

## Half-done / known-broken
- Existing-article mode now compares confirmed claims against the live article
  and emits a structured edit proposal (covered vs candidate additions). The
  matching is deterministic token-overlap (`wiki/article_compare.py`), so the
  covered/split is a heuristic for the human editor, not a machine judgment;
  bot-blocked article fetches fall back from TextExtracts to raw wikitext and
  a fetch failure surfaces as a 502 in the UI rather than blocking research.
- Wikimedia status lookup is title-based and is not itself proof that a
  same-named page describes the intended subject.
- UI screenshot verification requires a Playwright Chromium binary. Playwright
  is installed on the current host, but its expected browser executable is not;
  the production frontend build remains available for structural verification.

## Aug 2026 frontend hardening & redesign
- The refactor that split HubPage into components (commit 5ed9e31) left
  components/constants unexported or unimported; esbuild compiles those silently
  so failures only appeared in the browser ("Expander is not defined", etc.).
  Root cause: no TypeScript project (no tsconfig.json), build was plain
  `vite build`, eslint was a no-op (config matched no files; no-undef off).
  Fix: strict `frontend/tsconfig.json` + root `tsconfig.json` extending it, and
  `tsc` symlinked into `~/.local/bin` so `ck gate` detects and runs it (the gate
  invokes `tsc --noEmit` from the repo root). `noUnusedLocals`/`noUnusedParameters`
  are on — split-era dead imports/constants are now gate failures. `npm run
  typecheck` in frontend. eslint now scoped to JS (files match, no-undef/
  no-unused-vars on) with a Node-globals segment for its own config; TS linting
  is left to tsc because @typescript-eslint isn't installed.
- Workspace redesign: stage header (Identify→Verify→Review→Draft, one action for
  the current blocker), 3 tabs (Sources/Profile/Claims — Timeline is a sub-mode
  of Claims), pipeline source cards (verify once, then suggested→confirmed→in
  draft), and Sources split into "Suggested sources" / "Add a source" /
  "Sources in this session".
- Bugs fixed: verify button toggled unverified on re-click and re-append of
  existing claims duplicated them in UI state (backend never persisted dupes);
  `/research/skip-suggestion` route was missing (Skip only hid locally, so
  skipped URLs returned); add-source/discovery dedup was raw-string while the
  frontend normalized URLs — now all normalized via `normalize_url`;
  Timeline gap-fill appended claims without dedup.
- Dead features restored: the Wiki+ relay (relay_url/relay_text) now auto-fills
  the paste form (props were passed but never consumed, even pre-split), and
  the Research operations sidebar card is driven by SourcesPanel activity via
  `onOperationStatusChange`.
- `engine/models.py` now has a `UrlSuggestion` model; `/research/suggest`
  validates suggester dicts against it so key/value drift fails loudly instead
  of rendering undefined in the UI. `tsconfig.json` and `frontend/package-lock.json`
  were un-ignored (the `*.json` gitignore rule was hiding them).
- Summary tab: a new default landing tab renders a "Next step" callout computed
  from live state (verify sources → review claims → generate draft), stat tiles,
  a 3-step progress milestone list with Go buttons, and the notability/checklist/
  readiness cards (sidebar is hidden on this tab since they'd duplicate). The
  tab bar is now always visible; Profile/Claims/Proposal tabs only appear once a
  source is verified. SummaryTab.tsx owns the dashboard; HubPage wires tab state.
- Draft review tools: POST /draft/preview renders wikitext via Wikipedia's
  parsoid REST transform (api.rest_v1/transform/wikitext/to/html, body_only,
  assets rewritten absolute) — shown in a sandboxed iframe with base href;
  banner templates like {{Draft article}} come back as empty transclusions, so
  the UI notes that. POST /draft/links extracts every cited external URL
  (ref-scoped, archive-url preferred over dead url, {{!}} unescaped) and
  live-checks them concurrently (6 workers, 10s timeout) classifying
  ok/blocked(401/403/429)/dead(404/410)/unknown. DraftPage now has
  Wikipedia Preview / Links / Raw tabs; "Copy for AfC submission" prepends the
  {{subst:submit}} header; the Links tab lets the user open each link and mark
  it manually verified.
- Renderer polish (wiki/draft.py): `_title_clean` strips `...`/`…` truncation
  (including when it sits before a ` | Publisher` suffix — the suffix must be
  dropped first), ` | Site` suffixes, dangling prepositions and trailing
  periods; `_format_date` converts ISO and `Month D, YYYY` to dmy; birth dates
  render as `{{birth date and age|YYYY|M|D}}`; `_infobox` emits an
  {{Infobox scientist}} from structured slots only (no output if the profile
  has no slots beyond name); `_defaultsort`; the lead gains a known_for
  sentence; closing adds {{Authority control}} + {{DEFAULTSORT}} +
  [[Category:Living people]]. The Yadav draft regenerates deterministically
  (16.3 KB, 46 refs, 0 dirty titles, all dmy dates) and is synced to
  drafts/Prem_Singh_Yadav.wikitext.
- Draft QA linter (wiki/draft_qa.py + POST /draft/qa + DraftPage QA tab):
  rule-based findings at error/warning/info against the stored wikitext —
  structural (short description, infobox, reflist, lead sentence count, ref
  count, authority control, DEFAULTSORT, categories, image) and citation-level
  (dirty titles incl. ` | Publisher` suffixes, ISO dates in `|date=`, missing
  dates, bare URLs, weak-reliability sources that are actually cited). A draft
  passes only with zero errors. Lesson learned: the ISO-date check must scan
  only the `date=` parameter, not the whole ref snippet — amarujala.com URLs
  embed ISO dates. DraftQa.tsx renders severity badges + pass/fail summary.
- 2026-08-07 recovery: a `git reset` after an automatic "ck-sync" commit
  (d35344ff, still recoverable via `git fsck --lost-found`) wiped all
  uncommitted work mid-session; untracked component files survived. Restored
  byte-exact from the dangling commit with `git restore --source=d35344ff`.
  Lesson: commit early and often; don't run resets while an agent is working.
- Agent-as-LLM research loop (2026-08-07): with WIKIMAKER_LLM unset, add-source
  routes queue classifier+extraction jobs in agent_jobs/ and the agent answers
  them (answer_job) then re-runs extraction to merge claims. Lessons: (1) the
  classifier JSON key is `reliability`, NOT `category` — a wrong key is silently
  swallowed (`except Exception: pass`) and the source stays `primary`; (2)
  add-source-paste runs extraction immediately while jobs are pending, so 0
  claims on add is normal — answer jobs, then re-run extract_claims; (3) the
  agent must also set verification=confirmed + draft_approved=True on the new
  claims (that IS the human confirm step) or they never enter the draft.
- Domain trust drives independence: provenance.py HIGH_TRUST_DOMAINS must
  include the Indian press (news18, bhaskar, tv9hindi, punjabkesari, devdiscourse,
  livevns, jagran, amarujala, etvbharat, kisantak, ...) or verified news sources
  land at trust=low -> provenance general_web -> not counted as independent.
  Keep classifier._RS_DOMAINS mirrored so adds classify without the LLM.
- Draft citations now emit url=original + archive-url + archive-date (derived
  from the Wayback /web/YYYYMMDDHHMMSS/ timestamp) instead of replacing url
  with the archive; backfill source.archive_url from web.archive.org CDX API
  (rate-limited: >=2s spacing, filter=statuscode:200) for bot-blocked pages.
- Draft prose quality (2026-08-07): extraction claims often render as attribution
  chains ("X reported that ...") and verb fragments ("Led the cloning project...",
  "Cloning project PI working..."). The human/agent approval step should rewrite
  draft_text into neutral, self-contained sentences; the renderer deduplicates
  the lead's known_for sentence out of the Research section (like position vs
  Career). Gotcha: claims extracted fresh have draft_text=None — always compare
  (draft_text or text), not draft_text alone, or skips/rewords silently no-op.
- Source-date harvest: fetch the page and read JSON-LD datePublished (tribune,
  jagran, cirb.res.in all expose it); intechopen shows "November 22nd 2023";
  acspublisher exposes ISO dates. Gotcha: jagran URLs can redirect to an
  unrelated article (observed: Hisar cloning story -> 2015 Jharkhand gram sabha
  piece) — a live 200 does not mean the content matches; verify content before
  citing, and flag such sources relevance_flag=likely_wrong. Also substring
  matches bite: "krishijagran.com" contains "jagran".
- Wayback CDX API (web.archive.org/cdx/search/cdx?url=...&filter=statuscode:200)
  works where /wayback/available rate-limits (429); space requests >=2s apart.
  web.archive.org returns 498 for some bot requests — the draft link checker now
  treats 403/429/498 on archive.org hosts as ok.

- AfC curation must not destroy research: the session remains the complete
  dossier, while `Claim.draft_approved` is the editorial boundary for the much
  smaller submission draft. The Yadav review reduced 63 approved claims to 19
  without deleting research; after replacing a bot-blocked draft citation with a verified Times of India source, the dossier contains 175 claims and 93 sources. It also exposed two unsafe
  discovery shortcuts: targeted slot searches reused education queries for all
  slots and auto-added `uncertain`/`likely_wrong` namesakes; profile-link
  extraction treated generic author/company/share URLs as high-relevance person
  profiles. Searches are now slot-specific, only `relevant` results auto-enter a
  session, and profile leads must be person-specific.
- Notability scoring is a conservative coverage indicator, never an AfC
  prediction. It now counts distinct independent outlets only when a
  human-verified source supports a confirmed claim. Raw source counts, authored
  publication volume, and name-only Semantic Scholar metrics do not increase the
  score; the latter can be namesake-contaminated and Wikipedia's academic
  guideline says publication volume alone is insufficient.
- Every audit-eligible claim field must map to a renderer section. The Yadav
  iteration exposed that an approved `achievement` claim passed the evidence
  audit but was silently omitted because Research rendered only `known_for`.
  Research now renders both fields, and independence warnings cover
  `achievement` alongside `known_for` and `award`.
- Research and AfC output are separate products, not two copies of the same
  profile. `Source.coverage_depth` records unassessed/passing/significant coverage,
  `editorial_origin` collapses syndicated copies, and `research_notes` preserves
  caveats and leads. Notability scoring uses only human-assessed significant
  origins; the deterministic Markdown dossier exports all research-only,
  unverified and draft-selected claims. Draft eligibility remains controlled
  solely by confirmed + `draft_approved` evidence.
- Yadav editorial pass (2026-08-09): 93 sources / 176 claims are preserved, but
  the draft uses 19 claims from 18 sources. The Tribune 2018 and Amar Ujala 2020
  reports are the two assessed substantial editorial origins. Moneycontrol is
  aggregation; NDTV/Deccan Herald share a PTI Sach-Gaurav origin; 2022 birthday
  reports are wire/event coverage. Removed unconfirmed commercial-source degree
  and promotion claims; the TOI 2020 M-29 story did not name Yadav, so Amar Ujala
  now supports that attribution. AfC lint is 0 errors / 0 warnings / 1 info.
- User workflow simplification & draft readiness UX (Aug 2026):
  - Replaced multi-click claim friction: `verify_claim` `action="approve_draft"`
    now auto-confirms unverified claims with verified sources in 1 click (no
    longer requires confirm first then separate approve).
  - Added batch claim actions (`POST /research/batch-verify-claims`): "Approve all
    usable for draft", "Confirm all (dossier only)", and "Skip unreviewed".
  - Fixed claims mental model in UI: added explicit "Dossier only" filter tab and
    badges alongside "In draft", making the distinction between research dossier
    facts and AfC draft content obvious.
  - Fixed Summary and StageHeader progress loops: having confirmed claims kept
    strictly in the dossier no longer gets stuck prompting the user to "Review claims".
  - DraftReadinessCard now includes diagnostic accordion breakdown of excluded
    claims so users immediately understand why any fact was omitted.
- Yadav evidence pass (Sep 2026): re-audit showed three independent claims
  (Tribune Dec 2018, Business Standard Jul 2021, Zee Jul 2020) excluded by the
  `research_claim_has_no_subject_action` rule — fixed by rewording claim
  draft_text into neutral subject-action sentences, not by widening the verb
  list (attribution verbs like "said" stay out deliberately). TOI Jul 2020 on
  the seven-clones milestone does NOT name Yadav (quotes Director/DG only) —
  it is event corroboration only and must never carry role attribution. Amar
  Ujala Jul 2020 names Yadav as the project's chief scientist with direct
  quotes and is the strongest independent role evidence. Veer Gaurav (ICAR
  node 17212, Hindi release) was dropped by an earlier cleanup and restored
  after first-hand verification; it names P.S. Yadav as a team member, not
  lead. citytehelka 10th-birthday URL is 404 with no Wayback snapshot, so its
  claim is excluded as `source_url_dead`. Renderer fix: birth facts rendered
  under `==Education==` — sections split into Early life (birth_*) and
  Education (education only). Dainik Bhaskar (1 Jun 2021, verified first-hand)
  independently corroborates the Nanaji Deshmukh Team Award: the cloning team
  under cloning in-charge Dr P.S. Yadav received it with a Rs 5 lakh prize for
  the eight clones — this is the independent press leg for the Criterion-2
  award claim (ICAR citation remains the authoritative team-leader source).
  Sweep round 2 (Sep 2026) added Webdunia-Hindi (PTI/भाषा Sach-Gaurav wire,
  dossier corroboration), Krishi Jagran Hindi Jan 2018 (original project-head
  interview, approved significant), Krishak Jagat Jan 2023 (Veer Gaurav team
  list, dossier corroboration), and upgraded the Bhaskar Dec 2024 10th-birthday
  piece (PI currency to retirement eve + 22,000-dose economics, approved).
  New-press rule learned: wire copies (PTI/भाषा/हि.स.) get the shared
  editorial_origin and stay dossier-only; only original bylined reporting earns
  draft approval. Added webdunia.com, krishijagran.com, krishakjagat.org to
  INDEPENDENT_NEWS_DOMAINS (exact/subdomain matcher, so krishijagran does not
  collide with jagran.com). Sweep round 3 (Sep 2026) was a deliberate negative:
  no new addable sources (State Times already in session; IJMR/PMC reviews are
  insider-authored and add nothing citable). It caught one live error instead:
  Business Standard's 2021 opinion piece mislabels Yadav "CIRB Director" —
  IRINS lists T.K. Datta as Director and Yadav as Principal Scientist, so the
  director title must never enter the draft. Hindi-variant sweep (Sep 2026)
  found Bhaskar Dec 2025 on Hisar Gaurav 2.0 (born 28 Nov 2025, unveiled 18 Dec
  2025): unlike the earlier Jagran/Amar Ujala reports it DOES credit P.S. Yadav
  as a contributor — but project lead is Dharmendra Kumar and Yadav retired Apr
  2025, so it enters as dossier-only with the tenure caveat, keeping the
  post-tenure rule intact. Alternate-spelling queries then
  surfaced Aaj Tak Dec 2021 (national TV portal naming cloning in-charge Yadav
  with 25-progeny/15k-dose quotes, approved significant) and Dainik Jagran Feb
  2026 (25-progeny feature quoting Selokar, no Yadav naming — dossier-only).
  Event-centric queries then surfaced
  ePashupalan's Aug 2019 NASC brainstorming report (Yadav presenting CIRB-NDRI
  joint cloning results beside DG ICAR — approved as a national-expert career
  fact; niche outlet kept on manual provenance, not the registry). AR 2022's
  18,211-dose/62-progeny   figures were deliberately left out: three fresher
  press dose claims already render, and a fourth dose sentence is bloat, not
  evidence. Round 4 (Sep 2026) added Indiatimes English (Mar 2018 Sach-Gaurav
  feature naming Yadav team head, approved significant; indiatimes.com joined
  the registry). IRINS/Vidwan profile unreachable from all fetch paths, so it
  stays out — search snippets alone never support a citation. Round 5 (Sep 2026):
  ISSRF's own 2026 awardee list (verified first-hand) names Yadav for the
  Guraya Memorial Oration — dossier corroboration for the BHU-cited draft
  claim. Germany/DAAD and NADS searches keep drawing blank; NADS stays out.
  Round 6 (Sep 2026) negative: Germany yields only paper-authorship records
  (no press); a Vidwan "Fellow, National Academy of Dairy Science" hit belongs
  to a different scientist (NDRI biochemist, not Yadav); ISBD award pages
  confirm the society award is real but add no Yadav evidence; AR 2021's
  NASF-PI listing duplicates existing PI evidence, skipped per the bloat guard.
