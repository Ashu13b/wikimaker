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
  get_provider() prints a loud one-time warning when it silently falls back to
  StubProvider.
- The Yadav draft regression test now reads a frozen fixture
  (tests/fixtures/Prem_Singh_Yadav.json) instead of the live session file, so
  session growth no longer breaks it.
- resume_session never repopulates claims from the stub provider
  (has_real_llm guard) — stub-extracted claims are fabricated and would
  silently pollute an otherwise clean session.
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
