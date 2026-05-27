"""
Standalone remote browser server.

Usage:
    python browser_server.py            # port 7070

Tunnel (add to your ssh command):
    -L 7070:localhost:7070

Then open http://localhost:7070 on your mobile browser.

Install Xvfb first for headed mode (lets you solve CAPTCHAs visually):
    sudo apt install -y xvfb
"""
from __future__ import annotations
import os, time, subprocess, threading, queue
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

PROFILE_DIR = Path.home() / ".wikimaker" / "browser_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
XVFB_DISPLAY = ":99"
PORT = 7070

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


def _dispatch(action: str, **args) -> Any:
    """Send a command to the browser thread and wait for the result."""
    cmd = _Cmd(action=action, args=args)
    _q.put(cmd)
    if not cmd.done.wait(timeout=35):
        raise TimeoutError(f"browser command '{action}' timed out")
    if cmd.error:
        raise RuntimeError(cmd.error)
    return cmd.result


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
    _headed = _try_start_xvfb()
    if _headed:
        os.environ["DISPLAY"] = XVFB_DISPLAY
    mode = "headed (Xvfb)" if _headed else "headless"
    print(f"[browser] {mode} mode — http://localhost:{PORT}")

    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth
    stealth = Stealth()
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=not _headed,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-setuid-sandbox",
                  "--disable-blink-features=AutomationControlled"],
            viewport={"width": 390, "height": 844},
        )
        live = [p for p in ctx.pages if not p.is_closed()]
        page = live[0] if live else ctx.new_page()
        stealth.apply_stealth_sync(page)
        _running = True

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
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    cmd.result = {"url": page.url, "title": page.title()}
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
    if _xvfb:
        _xvfb.terminate()


app = FastAPI(title="remote-browser", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── API endpoints ──────────────────────────────────────────────────────────────

@app.get("/screenshot")
def screenshot():
    if not _running:
        return Response(content=b"", media_type="image/jpeg", status_code=503)
    data = _dispatch("screenshot")
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


class NavReq(BaseModel):
    url: str

@app.post("/navigate")
def navigate(req: NavReq):
    if not _running:
        return {"error": "browser not ready", "url": ""}
    try:
        result = _dispatch("navigate", url=req.url.strip())
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
    if not _running:
        return {"error": "browser not ready"}
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


# ── Embedded single-page UI ────────────────────────────────────────────────────

@app.get("/")
def index():
    return HTMLResponse(BROWSER_HTML)


BROWSER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Remote Browser</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
:root {
  --bg: #18181b;
  --surface: #27272a;
  --border: #3f3f46;
  --text: #e4e4e7;
  --muted: #71717a;
  --accent: #3b82f6;
  --accent-dim: rgba(59,130,246,0.15);
}
html, body { height: 100%; background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; overflow: hidden; }
body { display: flex; flex-direction: column; }

/* ── Toolbar ── */
#toolbar {
  display: flex; align-items: center; gap: 5px;
  padding: 7px 8px; background: var(--surface);
  border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.nav-btn {
  background: var(--bg); border: 1px solid var(--border); color: var(--text);
  width: 34px; height: 34px; border-radius: 8px; font-size: 18px;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  user-select: none; flex-shrink: 0;
}
.nav-btn:active { background: var(--border); }
#url-bar {
  flex: 1; min-width: 0; background: var(--bg); border: 1px solid var(--border);
  color: var(--text); padding: 7px 11px; border-radius: 8px; font-size: 13px;
  outline: none;
}
#url-bar:focus { border-color: var(--accent); }
#go-btn {
  background: var(--accent); border: none; color: white;
  padding: 7px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; flex-shrink: 0;
}
#go-btn:active { opacity: 0.85; }

/* ── Viewport ── */
#viewport {
  flex: 1; background: #000; overflow: hidden; position: relative;
  display: flex; align-items: flex-start; justify-content: center; touch-action: none;
}
#screen {
  width: 100%; height: 100%; object-fit: contain; object-position: top center;
  display: block; cursor: crosshair; user-select: none; -webkit-user-select: none;
}
#overlay {
  position: absolute; inset: 0; pointer-events: none;
  display: flex; align-items: center; justify-content: center;
}
#loading-msg {
  background: rgba(0,0,0,0.7); color: var(--muted); padding: 8px 16px;
  border-radius: 8px; font-size: 13px; display: none;
}
#url-status {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: rgba(0,0,0,0.65); color: var(--muted); font-size: 11px;
  padding: 2px 8px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;
  pointer-events: none; opacity: 0; transition: opacity 0.5s;
}

/* ── Bottom bar ── */
#bottom {
  display: flex; align-items: center; gap: 5px;
  padding: 7px 8px; background: var(--surface);
  border-top: 1px solid var(--border); flex-shrink: 0;
}
#type-input {
  flex: 1; min-width: 0; background: var(--bg); border: 1px solid var(--border);
  color: var(--text); padding: 7px 11px; border-radius: 8px; font-size: 14px;
  outline: none; autocomplete: off;
}
#type-input:focus { border-color: var(--accent); }
.act-btn {
  background: var(--bg); border: 1px solid var(--border); color: var(--text);
  padding: 7px 11px; border-radius: 8px; font-size: 13px; cursor: pointer;
  white-space: nowrap; flex-shrink: 0;
}
.act-btn:active { background: var(--border); }
#wiki-btn {
  background: var(--accent-dim); border: 1px solid var(--accent);
  color: var(--accent); padding: 7px 10px; border-radius: 8px; font-size: 12px;
  font-weight: 700; cursor: pointer; flex-shrink: 0;
}
#wiki-btn:active { background: var(--accent); color: white; }

/* ── Toast ── */
#toast {
  position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%);
  background: rgba(0,0,0,0.85); color: var(--text); padding: 8px 16px;
  border-radius: 10px; font-size: 13px; z-index: 100; display: none;
  white-space: nowrap; max-width: 90vw; text-overflow: ellipsis; overflow: hidden;
}
</style>
</head>
<body>

<div id="toolbar">
  <button class="nav-btn" id="btn-back" title="Back">&#8249;</button>
  <button class="nav-btn" id="btn-fwd" title="Forward">&#8250;</button>
  <button class="nav-btn" id="btn-reload" title="Reload">&#8635;</button>
  <input id="url-bar" type="url" inputmode="url" autocomplete="off"
         autocorrect="off" autocapitalize="none" spellcheck="false"
         placeholder="https://...">
  <button id="go-btn">Go</button>
</div>

<div id="viewport">
  <img id="screen" src="" alt="browser viewport" draggable="false">
  <div id="overlay"><div id="loading-msg">Navigating…</div></div>
  <div id="url-status"></div>
</div>

<div id="bottom">
  <input id="type-input" type="text" inputmode="text"
         autocomplete="off" autocorrect="off" autocapitalize="none"
         spellcheck="false" placeholder="Type and tap Send…">
  <button class="act-btn" id="btn-send">Send</button>
  <button class="act-btn" id="btn-enter">&#8629;</button>
  <button class="act-btn" id="btn-bs">&#9003;</button>
  <button id="wiki-btn" title="Send page to wikimaker">Wiki+</button>
</div>

<div id="toast"></div>

<script>
const POLL_MS = 600;
let pollTimer = null;
let navigating = false;

// ── Viewport sync ─────────────────────────────────────────────────────────────
async function syncViewport() {
  const vp = document.getElementById('viewport');
  const w = Math.round(vp.clientWidth);
  const h = Math.round(vp.clientHeight);
  if (w < 50 || h < 50) return;
  try {
    await fetch('/viewport', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ width: w, height: h }),
    });
  } catch (_) {}
}
window.addEventListener('resize', () => { syncViewport().then(() => refreshShot()); });

// ── Screenshot polling ────────────────────────────────────────────────────────
function startPoll() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(refreshShot, POLL_MS);
  syncViewport().then(() => refreshShot());
}

function refreshShot() {
  const img = document.getElementById('screen');
  img.src = '/screenshot?' + Date.now();
}

async function refreshInfo() {
  try {
    const d = await fetch('/info').then(r => r.json());
    if (d.url && d.url !== 'about:blank') {
      document.getElementById('url-bar').value = d.url;
      document.title = (d.title || 'Remote Browser').slice(0, 60);
      const st = document.getElementById('url-status');
      st.textContent = d.url;
      st.style.opacity = '1';
      setTimeout(() => { st.style.opacity = '0'; }, 2000);
    }
  } catch (_) {}
}

// ── Navigation ────────────────────────────────────────────────────────────────
async function navigate() {
  const url = document.getElementById('url-bar').value.trim();
  if (!url) return;
  setLoading(true);
  try {
    const d = await fetch('/navigate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    }).then(r => r.json());
    if (d.url) document.getElementById('url-bar').value = d.url;
    if (d.error) toast('Error: ' + d.error);
  } finally {
    setLoading(false);
    setTimeout(() => { refreshShot(); refreshInfo(); }, 200);
  }
}

function setLoading(on) {
  navigating = on;
  document.getElementById('loading-msg').style.display = on ? 'block' : 'none';
}

async function navAction(path) {
  setLoading(true);
  try {
    await fetch(path);
  } finally {
    setLoading(false);
    setTimeout(() => { refreshShot(); refreshInfo(); }, 400);
  }
}

// ── Click / tap handling ──────────────────────────────────────────────────────
let touchStart = null;

const screen = document.getElementById('screen');

screen.addEventListener('touchstart', e => {
  touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY, t: Date.now() };
}, { passive: true });

screen.addEventListener('touchmove', async e => {
  if (!touchStart) return;
  const dy = touchStart.y - e.touches[0].clientY;
  const dx = touchStart.x - e.touches[0].clientX;
  touchStart.x = e.touches[0].clientX;
  touchStart.y = e.touches[0].clientY;
  if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 3) {
    await fetch('/scroll', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delta: dy * 2.5 }),
    });
    refreshShot();
  }
}, { passive: true });

// Map a tap position on the <img> element to actual image coordinates,
// accounting for object-fit:contain letterboxing (object-position: top center).
function tapToImageCoords(tapX, tapY, imgEl) {
  const elW = imgEl.clientWidth;
  const elH = imgEl.clientHeight;
  const natW = imgEl.naturalWidth || 390;
  const natH = imgEl.naturalHeight || 844;
  const scale = Math.min(elW / natW, elH / natH);
  const rendW = natW * scale;
  const rendH = natH * scale;
  const offX = (elW - rendW) / 2; // center horizontally
  const offY = 0;                  // top vertically (object-position: top)
  return { x: tapX - offX, y: tapY - offY, img_w: rendW, img_h: rendH };
}

screen.addEventListener('touchend', async e => {
  if (!touchStart) return;
  const dt = Date.now() - touchStart.t;
  const endX = e.changedTouches[0].clientX;
  const endY = e.changedTouches[0].clientY;
  const moved = Math.hypot(endX - touchStart.x, endY - touchStart.y);
  touchStart = null;
  if (moved > 10 || dt > 600) return; // swipe or long-press, not a tap
  e.preventDefault();
  const rect = screen.getBoundingClientRect();
  const coords = tapToImageCoords(endX - rect.left, endY - rect.top, screen);
  await fetch('/click', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(coords),
  });
  setTimeout(() => { refreshShot(); refreshInfo(); }, 500);
}, { passive: false });

// Desktop mouse click fallback
screen.addEventListener('click', async e => {
  if ('ontouchstart' in window) return; // handled above
  const rect = screen.getBoundingClientRect();
  const coords = tapToImageCoords(e.clientX - rect.left, e.clientY - rect.top, screen);
  await fetch('/click', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(coords),
  });
  setTimeout(() => { refreshShot(); refreshInfo(); }, 500);
});

// ── Keyboard ──────────────────────────────────────────────────────────────────
async function sendType() {
  const inp = document.getElementById('type-input');
  if (!inp.value) return;
  await fetch('/type', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: inp.value }) });
  inp.value = '';
  setTimeout(refreshShot, 300);
}

async function sendKey(key) {
  await fetch('/key', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) });
  setTimeout(() => { refreshShot(); refreshInfo(); }, 350);
}

// ── Wiki+ relay ───────────────────────────────────────────────────────────────
async function sendToWikimaker() {
  toast('Reading page content…');
  try {
    const d = await fetch('/content').then(r => r.json());
    const params = new URLSearchParams({ relay_url: d.url, relay_text: d.text.slice(0, 30000) });
    // Wikimaker listens on same machine, port 5173 via Vite / port 8001 via backend
    window.open('http://localhost:5173/?' + params.toString(), '_blank');
    toast('Sent to wikimaker — switch to that tab');
  } catch (e) {
    toast('Could not reach wikimaker: ' + e.message);
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let toastTimer = null;
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.display = 'block';
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.style.display = 'none'; }, 2800);
}

// ── Wire up buttons ───────────────────────────────────────────────────────────
document.getElementById('btn-back').addEventListener('click', () => navAction('/back'));
document.getElementById('btn-fwd').addEventListener('click', () => navAction('/forward'));
document.getElementById('btn-reload').addEventListener('click', () => navAction('/reload'));
document.getElementById('go-btn').addEventListener('click', navigate);
document.getElementById('url-bar').addEventListener('keydown', e => { if (e.key === 'Enter') navigate(); });
document.getElementById('btn-send').addEventListener('click', sendType);
document.getElementById('btn-enter').addEventListener('click', () => sendKey('Enter'));
document.getElementById('btn-bs').addEventListener('click', () => sendKey('Backspace'));
document.getElementById('wiki-btn').addEventListener('click', sendToWikimaker);
document.getElementById('type-input').addEventListener('keydown', e => { if (e.key === 'Enter') sendType(); });

// ── Boot ──────────────────────────────────────────────────────────────────────
startPoll();
setInterval(refreshInfo, 2000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
