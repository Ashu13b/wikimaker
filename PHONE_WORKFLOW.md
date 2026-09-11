# PHONE_WORKFLOW — driving Wikimaker's UI from the Android phone

Validated 2026-08-22. The phone (Termux, tailnet `100.72.202.86`, sshd :8022,
user `u0_a509`) is the human companion screen for UI-driven research sessions.
The controller lives in the sibling repo `../termux/` (`phone_ctl.sh`,
`nx` at `/home/ubuntu/nexus/bin/nx`) — that setup was built for APK projects;
this is how it is used for a browser-UI project like Wikimaker.

## Topology (what works and why)

- **Phone → VM is fully blocked** by tailnet ACLs: every port on this VM
  (:22, :3890, :19080) times out from the phone. Direct browsing of
  `http://100.83.70.16:3890` does NOT work, and `nx cld2lcl` fails because it
  needs the phone to SSH into the VM ("ubu-ts" unreachable).
- **VM → phone works**: `nx phone:` / `ssh -p 8022 u0_a509@100.72.202.86`
  with `~/.ssh/id_ed25519` (BatchMode, no config entry needed).
- Therefore UI access = **reverse SSH tunnel from VM to phone**, binding
  Wikimaker on the *phone's own loopback*.

## Setup cycle

```bash
# 1. Server up (skip if already running; kills ports 3890/8001/7070 first)
nohup bash start.sh > /tmp/opencode/wikimaker_start.log 2>&1 &

# 2. Keep the phone awake
/home/ubuntu/nexus/bin/nx phone: termux-wake-lock

# 3. Reverse tunnel: phone loopback 3890 -> VM 3890
nohup ssh -p 8022 -o BatchMode=yes -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -N -R 3890:127.0.0.1:3890 u0_a509@100.72.202.86 \
  > /tmp/opencode/reverse_tunnel_3890.log 2>&1 &

# 4. Verify from the phone side
/home/ubuntu/nexus/bin/nx phone: "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3890/"
```

Phone browser then opens **http://127.0.0.1:3890** (same origin serves `/api`
and the companion browser at `/browser/`). No public exposure, no auth needed.

## Live shared desktop (default pathway; screenshot UI retired)

`browser_ui.html` is deleted (git history archives it); `/browser/` now serves
a landing page linking to the desktop, and the HubPage companion card embeds
the noVNC desktop directly. All `/browser/*` automation endpoints unchanged.

The `/browser/` page is screenshot polling (600ms JPEGs) — usable but laggy.
The live path is **noVNC on phone port 6901**, sharing the exact Xvfb display
(`:99`) the headed Chromium runs on: one session, human touches it on the
phone, the agent drives/reads it via `/browser/*` API simultaneously.

```bash
# x11vnc shares :99 as VNC :1 (port 5901); websockify bridges to 6901 with client
nohup x11vnc -display :99 -rfbport 5901 -shared -forever -noxdamage -ncache 0 -nopw -quiet -o /tmp/opencode/x11vnc.log &
nohup ~/.local/bin/websockify --web /tmp/opencode/novnc 6901 localhost:5901 > /tmp/opencode/websockify.log 2>&1 &
# second reverse forward next to the 3890 one
nohup ssh -p 8022 -o BatchMode=yes -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -N -R 6901:127.0.0.1:6901 u0_a509@100.72.202.86 \
  > /tmp/opencode/reverse_tunnel_6901.log 2>&1 &
```

Phone opens (one-tap, auto-scaled to the phone screen, auto-reconnects):

**http://127.0.0.1:6901/vnc.html?host=127.0.0.1&port=6901&path=websockify&autoconnect=true&resize=scale&quality=5&reconnect=true**

Mobile tuning: Xvfb runs a phone-sized desktop (`480x950`, not 1280x800) so
the Chromium window fills the phone with no pan/zoom; noVNC `resize=scale`
fits it to any screen. If the desktop ever resets to full-size, an Xvfb
restart at that geometry plus browser relaunch restores it (server restart
kills ports first per `start.sh` convention; session survives on disk —
resume it after).

Touch gestures (patched noVNC — one finger works like a phone browser):
tap = click, **one-finger swipe = scroll**, long-press = right-click,
two-finger swipe = scroll, pinch = zoom viewport. Stock noVNC maps
one-finger drag to text-select dragging; `scripts/novnc-touch-scroll.patch`
remaps it to wheel events (re-apply to `/tmp/opencode/novnc/core/rfb.js`
after a fresh noVNC download, then hard-refresh the phone page).

## The gated-fetch loop (who does what)

1. **Agent drives** the shared Chromium via `/browser/*` API (navigate, read,
   click, type) — same tabs the human sees in VNC.
2. **On a genuine wall** (CAPTCHA/Turnstile the headless render cannot pass),
   the agent toasts the phone with the site name and stops.
3. **Human solves** in the VNC desktop (same session, same cookies — solving
   anywhere else does not transfer) and says "solved".
4. **Agent resumes**: re-captures content, continues the walk.
5. One-off JS-gated reads with no wall: human may read directly in the
   phone's own Chrome and dictate; the agent binds via `add-sourced-claim`.

Notes: x11vnc/novnc/websockify were installed outside apt
(`apt` is dependency-broken on this host) — `.deb` direct-fetch for x11vnc,
`pip --user --break-system-packages` for websockify, noVNC v1.5.0 tarball from
GitHub into `/tmp/opencode/novnc`. `/tmp` does not survive reboot — reinstall
per above if the desktop is gone after a restart.

## Notifying the human

From the `../termux/` directory:

```bash
./phone_ctl.sh toast "Draft ready for claim review"
./phone_ctl.sh say   "Wikimaker needs your approval"
```

Use for human-gated moments: claims awaiting review, CAPTCHA in the companion
browser, draft QA finished.

## What the phone is good for here

- Claim review/approval and source verification decisions (the human-gated
  steps of the pipeline) away from the desk.
- CAPTCHA adjudication: open `/browser/` on the phone and tap through bot-walls
  while `fetch-blocked` walks blocked sources.
- Agent drives the API locally or via `nx phone:` curl; human adjudicates via
  the phone screen — matches the "verify via the actual UI" rule.

## Gotchas

- The tunnel dies when the phone changes network or Termux restarts.
  Re-establish with step 3 above; check first with the step-4 one-liner.
- Restarting Wikimaker (`bash start.sh`) does NOT require re-tunneling — the
  forward targets the VM port, not a process.
- If `ExitOnForwardFailure` fires, phone port 3890 is already taken; kill the
  stale listener first (`./phone_ctl.sh kill 3890` from `../termux/`).
- Plain `scp` never works to the phone (truncates); use `nx cp` — see
  `../termux/AGENTS.md`.

## Native Companion App (External Helper: `../android-browser/`)

A dedicated native Android APK (`../android-browser/app`) exists as an external mobile browsing and agent-bridge helper across projects. It supports native touch browsing routed through the VM's proxy, one-tap export to Wikimaker dossiers (`/api/research/add-source`), and on-device CAPTCHA resolution. Ongoing development of that app is maintained in its own workspace at `/home/ubuntu/Expeei/android-browser/`.

