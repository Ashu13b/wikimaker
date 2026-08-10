"""Headless browser fetcher using Playwright.

Works for sites that block plain requests but not real browsers:
- JavaScript-heavy pages that serve empty shells to requests
- Sites with basic bot detection (user-agent, navigator checks)

Does NOT bypass Cloudflare challenges (ResearchGate, some publishers).
For academic publishers use the API pipeline (researcher_ids.py).

Session cookies are persisted across runs in ~/.wikimaker/browser_session/
so the user only needs to pass any one-time checks once.
"""
from __future__ import annotations
from pathlib import Path
from .fetcher import FetchResult, _extract_text, BOT_WALL_RE

_SESSION_DIR = Path.home() / ".wikimaker" / "browser_session"

_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]

_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
window.chrome = {runtime: {}};
"""

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def fetch_with_browser(url: str, timeout_ms: int = 25_000) -> FetchResult:
    """Fetch url using headless Chromium with anti-detection patches.

    Uses a persistent browser profile so session cookies survive between runs.
    Returns FetchResult with blocked=True if content couldn't be retrieved.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        return FetchResult(url, "", method="browser", blocked=True)

    _SESSION_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(_SESSION_DIR),
                headless=True,
                args=_LAUNCH_ARGS,
                user_agent=_UA,
                ignore_https_errors=True,
                java_script_enabled=True,
            )
            page = ctx.new_page()
            page.add_init_script(_STEALTH_JS)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=8_000)
                except PWTimeout:
                    pass
            except PWTimeout:
                ctx.close()
                return FetchResult(url, "", method="browser", blocked=True)

            html = page.content()
            ctx.close()

        text = _extract_text(html)
        html_lower = html.lower()
        if BOT_WALL_RE.search(html_lower) and len(text) < 300:
            return FetchResult(url, "", method="browser", blocked=True)

        return FetchResult(url, text, method="browser", raw_html=html, blocked=False)

    except Exception:
        return FetchResult(url, "", method="browser", blocked=True)
