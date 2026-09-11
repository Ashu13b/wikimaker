"""
Remote browser server.

The FastAPI app here is mounted at `/browser` on the unified server
(`backend/main.py`, port 3890) and shown in the HubPage companion iframe. The
browser thread is started lazily on first request.

Legacy standalone mode (pre-unification): `python browser_server.py` served
this app on port 7070 for direct mobile access. The code path still exists but
the unified server is the supported way to run it.

Install Xvfb first for headed mode (lets you solve CAPTCHAs visually):
    sudo apt install -y xvfb
"""
from __future__ import annotations
import os
import time
import subprocess
import threading
import queue
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

# Challenge/bot-wall signatures — one shared vocabulary with the headless
# fetcher (engine.fetcher.BOT_WALL_RE) so the two can't drift.
from engine.fetcher import BOT_WALL_RE as _WALL_SIGNALS, is_safe_public_url

PROFILE_DIR = Path.home() / ".wikimaker" / "browser_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
XVFB_DISPLAY = ":99"
PORT = 7070

# Present as a normal desktop Chrome, not HeadlessChrome — several Indian press
# sites 403 the headless UA even though they serve humans fine.
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def looks_like_wall(text: str) -> bool:
    """True when rendered page text is a bot-wall/challenge, not real content."""
    return bool(text and _WALL_SIGNALS.search(text.lower()))

# ── Command queue — all Playwright calls go through this ──────────────────────
# Playwright's sync API is thread-bound; endpoints dispatch here and wait.

@dataclass
class _Cmd:
    action: str
    args: dict = field(default_factory=dict)
    done: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: str | None = None

_q: queue.Queue[_Cmd] = queue.Queue()
_headed = False
_running = False
_xvfb: Optional[subprocess.Popen] = None


def _dispatch(action: str, timeout: float = 35.0, **args) -> Any:
    """Send a command to the browser thread and wait for the result."""
    global _running
    if not _running and action != "status":
        start_browser()
    cmd = _Cmd(action=action, args=args)
    _q.put(cmd)
    if not cmd.done.wait(timeout=timeout):
        raise TimeoutError(f"browser command '{action}' timed out")
    if cmd.error:
        raise RuntimeError(cmd.error)
    return cmd.result


def browser_link_status(ctx: Any, urls: list[str]) -> dict[str, dict]:
    """Render each URL in a throwaway page (real fingerprint, JS runs, stealth).

    Fallback adjudicator for links plain requests cannot classify: a real
    browser either loads content (ok) or hits a challenge/wall (blocked). A new
    page is opened so the user's current companion page is left untouched.
    Returns the same shape as wiki.draft.check_draft_links.
    """
    page = ctx.new_page()
    try:
        try:
            from playwright_stealth import Stealth
            Stealth().apply_stealth_sync(page)
        except Exception:
            pass
        return _page_link_status(page, urls)
    finally:
        page.close()


def _page_link_status(page: Any, urls: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for u in urls:
        if not is_safe_public_url(u):
            out[u] = {"status": "unknown", "status_code": None, "final_url": u}
            continue
        try:
            resp = page.goto(u, wait_until="domcontentloaded", timeout=20_000)
            code = resp.status if resp else 200
            final = page.url
            if not is_safe_public_url(final):
                out[u] = {"status": "unknown", "status_code": None, "final_url": final}
                continue
            body = page.evaluate("document.body ? document.body.innerText : ''") or ""
            if code in (403, 429, 503) and _WALL_SIGNALS.search(body.lower()):
                out[u] = {"status": "blocked", "status_code": code, "final_url": final}
            elif 200 <= code < 400:
                out[u] = {"status": "ok", "status_code": code, "final_url": final}
            else:
                out[u] = {"status": "blocked", "status_code": code, "final_url": final}
        except Exception:
            out[u] = {"status": "unknown", "status_code": None, "final_url": u}
    return out


def _try_start_xvfb() -> bool:
    global _xvfb
    # Check if display is already usable (lock file exists = Xvfb already running)
    if Path(f"/tmp/.X{XVFB_DISPLAY.lstrip(':')}-lock").exists():
        os.environ["DISPLAY"] = XVFB_DISPLAY
        return True
    if _xvfb and _xvfb.poll() is None:
        return True
    try:
        _xvfb = subprocess.Popen(
            ["Xvfb", XVFB_DISPLAY, "-screen", "0", "1280x800x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(1.0)
        return _xvfb.poll() is None
    except FileNotFoundError:
        return False


def _browser_thread():
    """Owner of the Playwright context. Processes _q commands sequentially."""
    global _headed, _running
    print("[DEBUG] _browser_thread starting", flush=True)
    force_headless = os.environ.get("WIKIMAKER_HEADLESS", "0") == "1"
    print(f"[DEBUG] force_headless={force_headless}", flush=True)
    _headed = _try_start_xvfb() if not force_headless else False
    print(f"[DEBUG] _headed={_headed}", flush=True)
    if _headed:
        os.environ["DISPLAY"] = XVFB_DISPLAY
    mode = "headed (Xvfb)" if _headed else "headless"
    print(f"[browser] {mode} mode", flush=True)

    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth
    stealth = Stealth()
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=not _headed,
            user_agent=_UA,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-web-security",
                "--allow-running-insecure-content",
                "--disable-component-extensions-with-background-pages",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-ipc-flooding-protection",
                "--enable-automation=false",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-pings",
                "--password-store=basic",
                "--use-mock-keychain",
                "--disable-extensions-except=",
                "--disable-component-extensions-with-background-pages",
                "--disable-background-mode",
                "--disable-client-side-phishing-detection",
                "--disable-sync",
                "--disable-translate",
                "--disable-background-downloads",
                "--disable-default-apps",
                "--disable-hang-monitor",
                "--disable-prompt-on-repost",
                "--disable-domain-reliability",
                "--disable-breakpad",
                "--disable-component-update",
                "--disable-dev-tools",
                "--disable-extensions",
                "--disable-plugins-discovery",
                "--disable-print-preview",
                "--disable-speech-api",
                "--disable-permissions-api",
                "--disable-remote-fonts",
                "--disable-web-resources",
                "--disable-features=TranslateUI,BlinkGenPropertyTrees",
                "--metrics-recording-only",
                "--no-report-upload",
                "--enable-features=NetworkService,NetworkServiceInProcess",
                "--force-color-profile=srgb",
                "--use-gl=swiftshader",
                "--enable-gpu-rasterization",
                "--ignore-gpu-blocklist",
                "--disable-software-rasterizer",
            ],
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
            is_mobile=True,
            has_touch=True,
            locale="en-US",
            timezone_id="Asia/Kolkata",
            geolocation={"latitude": 26.9124, "longitude": 75.7873},
            permissions=["geolocation"],
            color_scheme="light",
            reduced_motion="reduce",
            forced_colors="none",
        )
        live = [p for p in ctx.pages if not p.is_closed()]
        page = live[0] if live else ctx.new_page()
        stealth.apply_stealth_sync(page)
        
        # Additional stealth: inject scripts to hide automation
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'hi']
            });
        """)
        
        _running = True
        print("[DEBUG] Browser thread ready, _running=True", flush=True)

        while True:
            try:
                cmd = _q.get(timeout=0.3)
            except queue.Empty:
                if page.is_closed():
                    break
                continue

            try:
                a = cmd.action
                if a == "screenshot":
                    cmd.result = page.screenshot(type="jpeg", quality=60, full_page=False)
                elif a == "navigate":
                    url = cmd.args["url"]
                    if "://" not in url:
                        url = "https://" + url
                    if not is_safe_public_url(url):
                        raise ValueError(f"Disallowed URL target: {url}")
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    if not is_safe_public_url(page.url):
                        raise ValueError(f"Disallowed redirect target: {page.url}")
                    cmd.result = {"url": page.url, "title": page.title()}
                elif a == "stop":
                    try:
                        ctx.close()
                    except Exception:
                        pass
                    cmd.result = {"ok": True}
                    break
                elif a == "info":
                    cmd.result = {"url": page.url, "title": page.title()}
                elif a == "click":
                    vp = page.viewport_size or {"width": 390, "height": 844}
                    bx = cmd.args["x"] / cmd.args["img_w"] * vp["width"]
                    by = cmd.args["y"] / cmd.args["img_h"] * vp["height"]
                    page.mouse.click(bx, by)
                    time.sleep(0.25)
                    cmd.result = {"ok": True}
                elif a == "type":
                    page.keyboard.type(cmd.args["text"])
                    cmd.result = {"ok": True}
                elif a == "key":
                    page.keyboard.press(cmd.args["key"])
                    time.sleep(0.15)
                    cmd.result = {"ok": True}
                elif a == "scroll":
                    page.mouse.wheel(0, cmd.args["delta"])
                    cmd.result = {"ok": True}
                elif a == "back":
                    page.go_back(wait_until="domcontentloaded", timeout=10000)
                    cmd.result = {"url": page.url}
                elif a == "forward":
                    page.go_forward(wait_until="domcontentloaded", timeout=10000)
                    cmd.result = {"url": page.url}
                elif a == "reload":
                    page.reload(wait_until="domcontentloaded", timeout=15000)
                    cmd.result = {"url": page.url}
                elif a == "content":
                    text = page.evaluate("document.body ? document.body.innerText : ''")
                    cmd.result = {"url": page.url, "text": text[:60000]}
                elif a == "set_viewport":
                    w, h = cmd.args["width"], cmd.args["height"]
                    page.set_viewport_size({"width": w, "height": h})
                    cmd.result = {"ok": True, "width": w, "height": h}
                elif a == "link_status_page":
                    cmd.result = browser_link_status(ctx, cmd.args.get("urls") or [])
                elif a == "status":
                    cmd.result = {"running": True, "headed": _headed, "url": page.url}
                else:
                    cmd.error = f"unknown action: {a}"
            except Exception as e:
                cmd.error = str(e)
            finally:
                cmd.done.set()

        _running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_browser_thread, daemon=True)
    t.start()
    # Wait until browser is ready (first successful status cmd or timeout)
    for _ in range(40):
        if _running:
            break
        time.sleep(0.25)
    yield
    stop_browser()


app = FastAPI(title="remote-browser", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── API endpoints ──────────────────────────────────────────────────────────────

@app.get("/screenshot")
def screenshot():
    data = _dispatch("screenshot")
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


class NavReq(BaseModel):
    url: str

@app.post("/navigate")
def navigate(req: NavReq):
    try:
        url = req.url.strip()
        if "://" not in url:
            url = "https://" + url
        if not is_safe_public_url(url):
            return {"error": f"Disallowed URL target: {url}", "url": ""}
        result = _dispatch("navigate", url=url)
        return result
    except Exception as e:
        return {"error": str(e), "url": ""}


@app.get("/info")
def info():
    if not _running:
        return {"url": "", "title": ""}
    return _dispatch("info")


class ViewportReq(BaseModel):
    width: int
    height: int

@app.post("/viewport")
def set_viewport(req: ViewportReq):
    w = max(320, min(req.width, 1920))
    h = max(400, min(req.height, 1920))
    return _dispatch("set_viewport", width=w, height=h)


class ClickReq(BaseModel):
    x: float
    y: float
    img_w: float
    img_h: float

@app.post("/click")
def click(req: ClickReq):
    _dispatch("click", x=req.x, y=req.y, img_w=req.img_w, img_h=req.img_h)
    return {"ok": True}


class TypeReq(BaseModel):
    text: str

@app.post("/type")
def type_text(req: TypeReq):
    _dispatch("type", text=req.text)
    return {"ok": True}


class KeyReq(BaseModel):
    key: str

@app.post("/key")
def press_key(req: KeyReq):
    _dispatch("key", key=req.key)
    return {"ok": True}


class ScrollReq(BaseModel):
    delta: float

@app.post("/scroll")
def scroll(req: ScrollReq):
    _dispatch("scroll", delta=req.delta)
    return {"ok": True}


@app.get("/back")
def go_back():
    return _dispatch("back")

@app.get("/forward")
def go_forward():
    return _dispatch("forward")

@app.get("/reload")
def reload():
    return _dispatch("reload")


@app.get("/content")
def get_content():
    """Return visible page text — used by the wikimaker 'Wiki+' relay."""
    return _dispatch("content")


@app.get("/status")
def status():
    if not _running:
        return {"running": False, "headed": _headed, "url": None}
    return _dispatch("status")


# ── Landing page ───────────────────────────────────────────────────────────────
# The live shared desktop (noVNC, port 6901) is the default phone pathway;
# the old screenshot-polling UI (browser_ui.html) is retired — git history
# is its archive. All /browser/* automation endpoints are unchanged.

@app.get("/")
def index():
    return HTMLResponse((Path(__file__).parent / "browser_home.html").read_text())


def start_browser() -> None:
    """Start the browser thread if not already running."""
    global _running
    if _running:
        return
    import threading
    t = threading.Thread(target=_browser_thread, daemon=True)
    t.start()
    for _ in range(40):
        if _running:
            break
        import time
        time.sleep(0.25)

def stop_browser() -> None:
    """Stop the browser thread, close Playwright context, and terminate Xvfb."""
    global _xvfb, _running
    if _running:
        try:
            _dispatch("stop", timeout=5)
        except Exception:
            pass
        _running = False
    if _xvfb:
        try:
            _xvfb.terminate()
            _xvfb.wait(timeout=3)
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
