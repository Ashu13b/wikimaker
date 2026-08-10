"""FastAPI backend for wikimaker — app wiring.

Route handlers live in backend/routes_research.py, backend/routes_draft.py, and
backend/routes_sessions.py; request models in backend/schemas.py; the session
store in backend/store.py. This module wires the app, mounts the static
frontend, and re-exports the public API names the frontend and tests use.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .store import SESSIONS_DIR, _sessions, _wiki_statuses  # noqa: F401  (public state)
from .schemas import (  # noqa: F401  (public request models)
    IdentifyRequest, ResearchRequest, AddSourceRequest, AddDocumentFact,
    AddSourcedClaimRequest, VerifyClaimRequest, AddSourcePaste, CrawlRequest,
    TargetedSearchRequest, DraftRequest, FindIdsRequest, RefreshPapersRequest, AssessSourceRequest,
)
from .routes_research import (  # noqa: F401  (public route handlers)
    identify, research_start, add_source, add_document_fact, add_sourced_claim,
    verify_claim, add_source_paste, deep_crawl, targeted_search_endpoint,
    auto_enrich_endpoint, article_proposal, get_session, verify_source,
    assess_source, reject_source, skip_suggestion, find_researcher_ids_endpoint,
    refresh_papers_endpoint, fetch_from_browser, fetch_blocked, suggest_urls,
    research_router,
)
from .routes_draft import (  # noqa: F401
    draft_audit, generate_draft, draft_links, draft_preview, draft_qa, draft_verify,
    draft_router,
)
from .routes_sessions import (  # noqa: F401
    resume_session, list_sessions, delete_session, sessions_router,
)

api_app = FastAPI(title="wikimaker")
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3890", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
api_app.include_router(research_router)
api_app.include_router(draft_router)
api_app.include_router(sessions_router)


# ── Unified App setup ───────────────────────────────────────────────────────
from contextlib import asynccontextmanager  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from browser_server import stop_browser, app as browser_app  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Remote browser thread is lazily initialized on demand via _dispatch
    yield
    # Clean up Xvfb/Playwright processes
    stop_browser()


# Create unified top-level app
app = FastAPI(title="wikimaker-unified", lifespan=lifespan)

# Add global CORS middleware to support local Vite dev server proxies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount sub-apps
app.mount("/api", api_app)
app.mount("/browser", browser_app)

# Serve compiled frontend React SPA statically
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.api_route("/", methods=["GET", "HEAD"])
    async def serve_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def serve_catchall(path: str):
        # Fallback to index.html for SPA client-side routing (React Router)
        return FileResponse(FRONTEND_DIST / "index.html")
