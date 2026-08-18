<!-- context-kit DOCS_MAP · v0.1.0 · generated 2026-08-18 18:20 UTC · sha ff7ced3 · host vnic-trading -->

# DOCS_MAP

Index of existing docs (headings only). Load the full file on demand. Oversized/transcript docs are demoted to a `cold` pointer — open them only when needed.

## ./
- `AGENT_CAPABILITIES.md`
  - Agent Capability Negotiation
    - Inspect
- `AGENT_KNOWLEDGE.md`
  - AGENT_KNOWLEDGE
    - Intent
    - Execution context
    - State
    - Decisions & rejected approaches
    - Half-done / known-broken
    - Aug 2026 frontend hardening & redesign
- `README.md`
  - Wikimaker
    - Key Features
    - System Architecture
      - Seams & Boundaries
    - The 4-Stage Research Workflow
      - 1. Identify
      - 2. Verify Sources
      - 3. Review Claims
      - 4. Draft & Verification
    - Quickstart
      - Prerequisites
      - Starting Wikimaker
    - Development & Testing
      - Running Tests
  - Run complete test suite
  - Run draft-specific tests
      - Frontend Development
      - Quality Gate
  - Full quality gate (pyright, ruff, pytest, tsc, eslint, boundaries)
  - Fast quality gate (typecheck and lint only)
  - Refresh codebase index maps
    - Wikipedia Policy Grounding
- `ROADMAP.md`
  - ROADMAP
    - Shipped
    - Next
    - Out of scope

## .agents/
- `.agents/skills/context-kit/SKILL.md`
  - Context-Kit: Agent Guidance & Execution Protocol
    - ⚡ Core Directives for Agents
    - 🔄 5-Step Execution Lifecycle
      - Step 1: Orient & Check State
      - Step 2: Zero-Guess Symbol & File Lookup
      - Step 3: Check Architectural Seams & Dependencies
      - Step 4: Focused Task Compartments
  - or declared compartment: sh .context-kit/ck compartment <name>
      - Step 5: Pre-Flight Gate Verification & Map Refresh
- `.agents/skills/root-cause-debug/SKILL.md`
  - Evidence-Based Root Cause Debugging
    - ⚡ Core Rules & Directives
    - 🔬 Investigation Workflow
      - Step 1: Capture the Exact Failure Signature
      - Step 2: Formulate & Test Hypotheses
      - Step 3: Write a Reproducing Test
      - Step 4: Fix and Verify
    - 📋 Required Debug Report
- `.agents/skills/seam-audit/SKILL.md`
  - Architectural Seam & Boundary Audit
    - ⚡ Core Rules & Directives
    - 🔍 Investigation Workflow
    - 📋 Required Audit Output

## docs/
- `docs/AFC_REVIEW_AND_HARDENING.md`
  - Wikipedia AfC Review & Draft Hardening Protocol
    - 1. The 5 Core AfC Decline Vectors & Built-in Defenses
    - 2. Multi-Sourcing Strategy (1 vs 2–3 Sources per Claim)
    - 3. Deduplication & Prose Neutrality Engine
    - 4. Multilingual & Regional Source Integration ([WP:NONENG](https://en.wikipedia.org/wiki/Wikipedia:Verifiability#Non-English_sources))
    - 5. Automated QA Linter Rule Summary (`wiki/draft_qa.py`)

## research/
- `research/Prem_Singh_Yadav_cv_verification.md`
  - Prem Singh Yadav: CV verification dossier
    - Verified and useful
    - Public links
    - Deeper annual-report and earlier-draft findings
    - Still unverified or unsuitable for the draft
    - Editorial coverage review (9 August 2026)
    - AfC rationale for the cloning milestone
    - Nature Portfolio publication review
    - Telomere, telomerase and book records
    - Patent search (10 August 2026)
    - Acceptance-strengthening pass (10 August 2026)
      - Newly leveraged sources
      - Award verification upgrades
      - Draft changes
    - National-academy and award-significance search (10 August 2026)
    - CV-to-source audit (10 August 2026)
      - Publication-count reconciliation (10 August 2026)
