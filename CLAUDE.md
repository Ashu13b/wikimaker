# wikimaker — AI Handover Document

**Last updated:** 2026-05-29  
**Repo:** github.com/Ashu13b/wikimaker  
**Owner:** ay.yadav53@gmail.com

---

## What this project is

Wikipedia AfC (Articles for Creation) draft maker for scientists and researchers —
primarily Indian academics. The user types a name, the system researches it across
the web and academic databases, the user verifies sources, and the system generates
a ready-to-submit Wikipedia draft with proper inline citations.

Target user: someone who wants to create a Wikipedia page for a scientist but
doesn't know how to navigate AfC policy, find reliable sources, or write wikitext.

---

## Three-server architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Frontend        │────▶│  Backend          │────▶│  browser_server   │
│  Vite/React      │     │  FastAPI          │     │  Playwright+Xvfb  │
│  port 3890       │     │  port 8001        │     │  port 7070        │
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

- **Frontend** (`frontend/`) — React + TypeScript, no framework. All state is in-memory per session.
- **Backend** (`backend/main.py`) — FastAPI. Persists sessions as JSON in `sessions/`. All research logic lives in `engine/`.
- **browser_server** (`browser_server.py`) — Standalone FastAPI + Playwright (headed via Xvfb). Provides a remote browser that the user can see as a screenshot and click on. Handles CAPTCHAs and login-walled sites.

### How to start all three

```bash
bash start.sh
# or manually:
python3 browser_server.py &
python3 -m uvicorn backend.main:app --port 8001 &
cd frontend && npx vite --port 3890 --host 0.0.0.0
```

---

## User workflow (frontend stages)

```
identify → loading → hub → draft
```

1. **identify** (`IdentifyPage.tsx`) — User types a person's name. System searches Wikidata/Wikipedia for candidates. User confirms the right person (or enters manually). Can also resume a previous session.

2. **loading** (`ResearchPage.tsx`) — Calls `POST /research/start`. Backend fetches auto-sources (Semantic Scholar, web search, ORCID), classifies them, scores notability, extracts initial claims. Shows an animated progress bar.

3. **hub** (`HubPage.tsx`) — The main workspace. Four tabs:
   - **Sources** — suggestion queue + confirmed sources (sub-tabs: All / Research / News / Profile)
   - **Wikipedia Profile** — slot-by-slot view (birth date, affiliation, awards, etc.) with source quality indicators
   - **Timeline** — chronological view of all dated claims
   - **Review** — unverified claims queue for user to confirm/edit/skip

4. **draft** (`DraftPage.tsx`) — Rendered wikitext (English + optional Hindi). Copy-paste into Wikipedia.

---

## Engine modules (`engine/`)

| File | Purpose |
|---|---|
| `models.py` | Pydantic models: `PersonProfile`, `Source`, `Claim`, `NotabilityResult` |
| `identifier.py` | Wikidata/Wikipedia search to find person candidates |
| `researcher.py` | Orchestrates source fetching; `fetch_auto_sources()` is the main entry point |
| `fetcher.py` | Multi-strategy URL fetcher: browser_server → direct → ORCID → Wayback → headless. **PDF-aware**: detects `application/pdf` and extracts text via pdfminer.six / pypdf |
| `fetcher_browser.py` | Headless Playwright fallback (stealth mode) |
| `classifier.py` | LLM-based source reliability: `reliable_secondary` / `primary` / `self_published` / `unreliable` |
| `extractor.py` | LLM extracts structured claims from source snippets. Each claim has `field`, `text`, `date_context` |
| `relevance.py` | Flags sources as `relevant` / `uncertain` / `likely_wrong` (wrong-person detection) |
| `notability.py` | Scores WP:GNG notability from source set. Returns score 0–1, label, RS count |
| `crawler.py` | Graph crawler: follows links outward from seed URLs. **Temporal variants**: when a PDF mentions the person, auto-queues prior-year URLs (2026→2025→2024→2023) |
| `suggester.py` | Goal-directed suggestion engine. Pass 1: profile links from confirmed sources. Pass 2: LLM-generated web searches anchored to affiliation+field |
| `link_extractor.py` | Scans fetched HTML for profile-shaped outbound links (ORCID, scholar, faculty pages) |
| `author_check.py` | For DOI sources: verifies person is actually an author (Crossref + author name matching) |
| `researcher_ids.py` | Finds/validates researcher IDs: ORCID, Google Scholar, Semantic Scholar, OpenAlex, Scopus |
| `llm.py` | LLM provider abstraction. `get_provider()` returns Claude, Gemini, or StubProvider |

### `wiki/` modules

| File | Purpose |
|---|---|
| `wiki_check.py` | Checks if a Wikipedia page / AfC draft already exists for this person |
| `wikitext.py` | Renders `PersonProfile` → wikitext via LLM prompt |

---

## Key design decisions

### Claims only extracted on source confirmation
Sources are added to the profile immediately but claims are only extracted when the
user clicks "Confirm & extract claims" on a source card. This prevents polluting the
claim list with wrong-person results.

### browser_server command queue (thread safety)
Playwright must run on a single thread. All browser operations go through a
`queue.Queue[_Cmd]` — endpoints dispatch commands and block on a `threading.Event`.
The `_browser_thread` owns all Playwright state. Never call page methods from
endpoint threads.

### Stealth + headed browser
browser_server runs Chromium with `playwright-stealth` and a real Xvfb display.
This bypasses most bot detection. User can see the browser as a live screenshot
and tap/click to solve CAPTCHAs.

### Viewport auto-sync
When the user opens port 7070 on their phone, the page JS measures the available
viewport (excluding toolbar) and calls `POST /viewport` to resize the Playwright
browser to match. Also fires on window resize (handles rotation).

### Temporal URL crawling
When the crawler fetches a PDF that mentions the person, it auto-queues URLs with
prior years substituted: `annual-report-2026.pdf` → also tries 2025, 2024, 2023.
This implements the "intelligent crawl" — find one annual report, get the series.

### Source classification tabs (frontend only)
`categorizeSource()` in `HubPage.tsx` maps sources to display tabs:
- **Research**: `reliable_secondary` sources, DOI domains, Semantic Scholar, ORCID, Google Scholar
- **Profile**: `.ac.in`, `.edu`, `.gov.in`, ResearchGate (profile URLs), LinkedIn, institutional crawl results
- **News**: everything else

ResearchGate publication URLs (`/publication/`) go to Research; profile URLs (`/profile/`) go to Profile.

### `date_context` on claims
The extractor is instructed to include a verbatim date/range from the source text
for temporal claims (affiliation, position, award, education). Anti-hallucination
rule: omit entirely if no year appears verbatim. Used by the Timeline tab.

---

## LLM configuration

```bash
# Default — uses Claude (requires ANTHROPIC_API_KEY)
WIKIMAKER_LLM=claude  # or unset

# Gemini (fast + cheap for extraction)
WIKIMAKER_LLM=gemini
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-1.5-flash  # optional override

# Offline stub (rule-based, no API needed)
WIKIMAKER_LLM=stub
```

Falls back to `StubProvider` (rule-based) if the chosen provider's key is missing.

---

## Backend API endpoints (key ones)

| Method | Path | Purpose |
|---|---|---|
| POST | `/identify` | Search for person candidates |
| POST | `/research/start` | Full auto-research pipeline |
| POST | `/research/add-source` | Add a URL as a source |
| POST | `/research/add-source-paste` | Add source with user-pasted text |
| POST | `/research/fetch-from-browser` | Import whatever page is open in browser_server |
| POST | `/research/source/verify` | Confirm source + extract claims |
| POST | `/research/source/reject` | Remove source + its claims |
| POST | `/research/crawl` | Deep crawl from seed URLs |
| POST | `/research/suggest` | Get ranked URL suggestions |
| POST | `/research/targeted-search` | Search for a specific Wikipedia slot |
| POST | `/research/find-ids` | Find researcher IDs (ORCID, Scholar, etc.) |
| POST | `/draft` | Generate wikitext |
| GET | `/session/{name}` | Load saved session |

---

## Data persistence

Sessions are saved as JSON in `sessions/{name}.json`. The `sessions/` directory
and `*.json` files are gitignored. Each save writes the full `PersonProfile` state.

---

## Frontend file map

| File | Role |
|---|---|
| `src/App.tsx` | Stage router (identify → loading → hub → draft) |
| `src/types.ts` | All TypeScript interfaces mirroring Pydantic models |
| `src/api.ts` | All fetch calls to backend (port 8001) |
| `src/pages/IdentifyPage.tsx` | Name search + candidate confirmation |
| `src/pages/ResearchPage.tsx` | Loading screen during auto-research |
| `src/pages/HubPage.tsx` | Main workspace (largest file ~1400 lines) |
| `src/pages/DraftPage.tsx` | Wikitext display + copy |
| `src/components/CandidateCard.tsx` | Person card shown during identify |

### HubPage internal structure
- `SourcesPanel` — suggestion queue, source cards, paste/crawl expanders
- `TimelineTab` — chronological claim view grouped by year
- `ProfileTab` — slot grid (infobox fields) with fill actions
- `ClaimsSection` — claim review queue (pending tab)
- `SourceCard` — individual source with verify/reject actions
- `NotabilityCard`, `ChecklistCard` — sidebar widgets

---

## Wiki+ relay flow

browser_server has a "Wiki+" button. When clicked on a page, it opens:
`localhost:3890/?relay_url=URL&relay_text=ENCODED_TEXT`

`App.tsx` reads the query params on mount, sets `relayPending`, passes it down to
`HubPage → SourcesPanel` which auto-fills the paste panel with the URL and text.

---

## Known issues / gotchas

- `CORSMiddleware` in `backend/main.py` allows `localhost:3890` (start.sh) and `localhost:5173` (Vite default). Add new origins here if the port changes.
- `sessions/` directory is gitignored — session data is local only.
- browser_server starts Xvfb on display `:99`. If another Xvfb is already running on `:99`, it reuses it (checks `/tmp/.X99-lock`).
- Temporal crawling only triggers during `deep_crawl` (manual crawl), not during auto-research. Could be added to `fetch_auto_sources` later.
- The `StubProvider` extractor is rule-based and misses many facts — always use real LLM for production.

---

## Pending / future work

- Gap detection in Timeline: flag periods with no sourced claims, drive suggestion queries at those gaps
- Cross-claim validation: born 1950 + PhD "at age 22" = 1972, sanity-check dates
- Time-anchored suggestions: if uncovered 2008–2015, search queries should include those years
- Wikitext generator should use `date_context` for narrative ("served as Director from 2005 to 2015")
- CORS origins list in `backend/main.py` should match `start.sh` port
- PDF person-name search: before queuing temporal variants, confirm name appears in the PDF text (already done — `mentions > 0` check in crawler)
