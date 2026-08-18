# Wikimaker

**Wikimaker** is a local research workspace and deterministic drafting engine for biographical Wikipedia articles. It automates identity resolution, multi-outlet source discovery, provenance classification, and claim verification, producing audit-ready Wikipedia **Articles for Creation (AfC)** drafts and comprehensive research dossiers.

---

## Key Features

- **Subject-First Identity Resolution**: Disambiguates individuals across general web, Wikidata, and Wikipedia before research begins. Supports living researchers, academics, and public figures without requiring pre-existing Wikimedia entities.
- **Dual-Layer Evidence Model**:
  - **Research Dossier**: Full repository of all retained sources, notes, and confirmed findings.
  - **AfC Draft Boundary**: Only explicitly approved, human-verified claims backed by reliable secondary sources enter the generated wikitext.
- **Deterministic Server-Owned Drafting**: Wikitext is rendered strictly from structured, verified evidence via [`wiki/draft.py`](wiki/draft.py). No LLM hallucinations, invented citations, or fabricated prose.
- **Companion Remote Browser**: Integrated Playwright browser (`/browser`) for auto-resolving bot-blocked pages (Cloudflare/CAPTCHAs), testing page liveness, and live DOM extraction.
- **AfC Quality Gate & Linting**: Built-in static AfC checker (`wiki/draft_qa.py`) and live link verifier (`wiki/draft_verifier.py`) testing structural compliance, MOS formatting, dmy dates, dirty titles, and link health.
- **Agent-as-LLM Architecture**: Falls back smoothly from real LLM APIs (Claude/Gemini/Vertex AI) to coding-agent job queues (`agent_jobs/`), ensuring deterministic offline operation.

---

## System Architecture

Wikimaker runs as a unified single-service architecture on port `3890`:

```
┌─────────────────────────────────────────────────────────────┐
│                      Wikimaker (Port 3890)                  │
├──────────────────────────────┬──────────────────────────────┤
│ FastAPI Backend (/api)       │ React Frontend (dist/)       │
│ • Identity & Search APIs     │ • Summary & Milestones       │
│ • Source & Claim Pipelines   │ • Source Pipeline Manager    │
│ • Session Store (JSON)       │ • Claims Review & Dossier    │
│ • Draft Audit & QA Linter    │ • Wikipedia Live Preview     │
├──────────────────────────────┴──────────────────────────────┤
│ Playwright Companion Browser (/browser)                     │
│ • Live Link Adjudication · Bot-Wall Fallback · Page Capture │
└─────────────────────────────────────────────────────────────┘
```

### Seams & Boundaries
- `backend/`: API route handlers, request schemas, and session persistence.
- `engine/`: Search scrapers, source classifiers, relevance flaggers, and claim extractors.
- `wiki/`: Deterministic wikitext renderer (`draft.py`), AfC QA linter (`draft_qa.py`), and link verifiers (`draft_verifier.py`).
- `frontend/`: React + TypeScript UI built with Vite.
- `sessions/`: JSON session storage (keyed by immutable `py-<slug>-<hex>` IDs).

---

## The 4-Stage Research Workflow

```
1. IDENTIFY ──────► 2. VERIFY ──────► 3. REVIEW ──────► 4. DRAFT & SUBMIT
   Disambiguate        Confirm Sources     Triage Claims       Generate wikitext
   & check status      & extract facts     (Draft vs Dossier)  Verify links & AfC lint
```

### 1. Identify
Enter the subject's name, field, and affiliation. The system probes Wikipedia and Wikidata for existing articles/drafts and web clues, categorizing the workspace route:
- **`clear`**: No existing article → New AfC draft workspace.
- **`draft`**: Existing draft → Draft improvement mode.
- **`exists`**: Existing article → Live article comparison and diff proposal.
- **`deleted`**: Prior deletion review required.

### 2. Verify Sources
Discover sources via automated sweeps, targeted slot searches, or manual URL / text paste. Sources are classified into:
- **Independent Secondary** (National news, independent investigative reports).
- **Institutional / Primary** (University pages, annual reports, official institute rosters).
- **Authored Publications** (Journal papers, book chapters, conference proceedings).

*Note*: Verifying a source extracts candidate claims into the session without polluting the draft.

### 3. Review Claims
Triage AI-extracted claims:
- **`+ Draft`**: Approve claim for compilation into the Wikipedia draft.
- **`✓ Dossier`**: Confirm claim to preserve it in the research dossier only (keeps the Wikipedia article concise).
- **`✎ Edit`**: Reword the claim for neutrality or precision before approving.
- **`✗ Skip`**: Reject irrelevant or unreliable facts.
- **⚡ Batch Actions**: 1-click batch approval for all usable independent facts.

### 4. Draft & Verification
The deterministic engine audits evidence requirements:
- **AfC Evidence Audit**: Requires ≥2 distinct independent secondary outlets and citable career/identity evidence.
- **AfC Linting**: Checks lead length, ref count, infobox fields, date formats, and category tags.
- **Live Link Verification**: Probes all cited URLs and uses the companion browser to adjudicate bot-protected links.
- **1-Click Copy**: Export clean wikitext with `{{subst:submit}}` ready for Wikipedia AfC submission.

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Linux / macOS / WSL

### Starting Wikimaker
Run the unified start script (builds the frontend and starts the server on port `3890`):

```bash
bash start.sh
```

Open [http://localhost:3890](http://localhost:3890) in your browser.

---

## Development & Testing

### Running Tests
All tests are isolated from live user sessions via tmp directory fixtures:

```bash
# Run complete test suite
pytest

# Run draft-specific tests
pytest tests/test_draft.py
```

### Frontend Development
```bash
cd frontend
npm run dev        # Local Vite dev server
npm run typecheck  # TypeScript strict typecheck (tsc --noEmit)
npm run build      # Production frontend build
```

### Quality Gate
Wikimaker uses context-kit for continuous quality auditing:

```bash
# Full quality gate (pyright, ruff, pytest, tsc, eslint, boundaries)
sh .context-kit/ck gate

# Fast quality gate (typecheck and lint only)
sh .context-kit/ck gate --fast

# Refresh codebase index maps
sh .context-kit/ck build
```

---

## Wikipedia Policy Grounding

Wikimaker is built from the ground up to uphold Wikipedia's core content policies:
- **[WP:V](https://en.wikipedia.org/wiki/Wikipedia:Verifiability)** (Verifiability): No assertion exists without an accessible, verified source.
- **[WP:NPOV](https://en.wikipedia.org/wiki/Wikipedia:Neutral_point_of_view)** (Neutral Point of View): Facts are stated neutrally without editorializing.
- **[WP:GNG](https://en.wikipedia.org/wiki/Wikipedia:Notability)** & **[WP:ACADEMIC](https://en.wikipedia.org/wiki/Wikipedia:Notability_(academics))**: Strict separation between primary authored works and independent secondary coverage.
