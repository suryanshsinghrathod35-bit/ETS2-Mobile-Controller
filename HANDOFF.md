# ETS2 Phone Controller: handoff note

Paste this into a new chat (with server.py and static/index.html attached, or the GitHub link) to continue without re-reading the old conversation.

Repo: https://github.com/suryanshsinghrathod35-bit/ETS2-Mobile-Controller (public). Note: the chat's web fetch tool cannot open GitHub (robots.txt), but `git clone` inside the sandbox works, so ask Claude to clone it.

## Goal
Use an Android phone as a wireless controller for Euro Truck Simulator 2 on a Windows 11 laptop: tilt steering, throttle/brake pedals, and buttons (indicators, lights, horn, wipers, cruise control, trailer, Enter, pause, etc.). ETS2 keybinds are default except where noted below. Home WiFi has 2.4 GHz and 5 GHz; the setup must work on either.

## How to run
Easiest: double-click **`start-server.bat`** in the project folder. It asks for Administrator permission, changes to its own folder, activates the venv, runs `python server.py` and keeps the window open if the server stops. To force an IP, edit its `python server.py %*` line to e.g. `python server.py 192.168.1.5`.

Manual way:
```
cd $HOME\Desktop\ets2-controller
venv\Scripts\activate
python server.py        # optional: python server.py <laptop-ip>
```
- **Run the server AND ETS2 both as Administrator** (or both normal). With mixed privilege levels the keyboard buttons do nothing, because Windows blocks a normal process from sending keys to an elevated one. Both as Administrator is what works on this machine. To make ETS2 always start elevated: right-click its .exe > Properties > Compatibility > Run as administrator.
- A terminal opened as Administrator starts in System32: `cd` to the project folder first (the .bat does this itself).
- The first Windows Firewall popup needs "Private networks" ticked.
- Scan the QR code on the phone, tap Advanced > Proceed past the self-signed certificate warning, tap "Start driving".
- Editing static/index.html needs only a phone page reload (hard-reload if it looks stale). Editing server.py needs a server restart (Ctrl+C, run again).
- ETS2 must be the focused window for the keyboard buttons to work (the gamepad axes work regardless of focus).

## Folder layout
```
ets2-controller/
  venv/                (not in git)
  server.py
  static/index.html
  certs/               (auto-generated per IP, not in git)
  test_pad.py          (old virtual-gamepad test)
  ViGEmBus_1.22.0_x64_x86_arm64.exe   (driver installer, also in the repo)
  start-server.bat     (double-click launcher, self-elevates)
  requirements.txt     (vgamepad, websockets, qrcode, pydirectinput, cryptography)
  .gitignore           (venv/, certs/, __pycache__/)
  README.md            (GitHub README: features, setup, key table, troubleshooting)
  HANDOFF.md
  docs/                (put README screenshots/GIF here, e.g. phone-ui.png)
```

## Architecture
Phone page (HTTPS) <-> wss://<laptop-ip>:8443/ws <-> server.py
- Steering and pedals -> vgamepad virtual Xbox 360 controller (ViGEmBus driver) -> ETS2.
- Buttons -> pydirectinput scan-code key presses -> ETS2 (needs the game focused).

- HTTPS is required because Android Chrome blocks motion sensors on plain HTTP.
- server.py serves the page and the WebSocket on one port (websockets library, process_request).
- Python 3.14, packages: vgamepad, websockets, qrcode, pydirectinput, cryptography.

## Message protocol (JSON over WebSocket)
- Server to phone: `hello` (connection acknowledged), `pong` (echoes `ts`).
- Phone to server: `ping {ts}`, `lat {ms}`, `steer {v: -1..1}`, `throttle {v: 0..1}`, `brake {v: 0..1}`, `btn {id, down: true|false}`.

## Controller mapping (server.py)
- `apply_state`: left stick X = steering; left stick Y = throttle minus brake (ETS2 default Y axis); triggers also carry throttle (RT) and brake (LT) but binding them in ETS2 did not work well (both triggers appear as one merged Z axis).
- `KEYMAP` dict at the top of server.py maps a button id to (key, mode). Mode `tap` = 0.12 s press on touch-down; mode `hold` = key held while the button is held. Changing a button between tap and hold is a one-word edit in KEYMAP (server restart needed).

| Button id | Key | Mode |
|---|---|---|
| left | `[` | tap |
| right | `]` | tap |
| hazard | `f` | tap |
| lights | `l` | tap |
| highbeam | `k` | tap |
| horn | `h` | hold |
| wipers | `p` | tap |
| parking | `space` | tap |
| engine | `e` | tap |
| cruise | `c` | tap |
| trailer | `t` | tap (attach/detach) |
| enter | `enter` | hold (tolls, job menu, confirm) |
| pause | `esc` | tap (opens the ETS2 pause menu) |

- Key names are pydirectinput names. Unknown names fail silently.
- Every button press is logged in the server console as `[btn] <id> down -> key '<k>' (<mode>)`. If that line appears but nothing happens in-game, it is a focus/admin/keybind issue; if it does not appear, the phone page is stale. A failed key press prints `[btn] key press failed: ...` and does not drop the phone.
- Safety: on disconnect the server zeroes state, releases all held keys and resets the gamepad.

## Phone page features (static/index.html)
- Start screen: fullscreen, landscape lock, wake lock, auto-calibrate. Leaving fullscreen shows it again and releases controls.
- Tilt steering: devicemotion, angle = atan2(gy, gx), minus calibrated offset, smoothed (SMOOTH 0.35), 2 degree deadzone. Clockwise = right.
- Settings saved in localStorage: sensitivity (degrees for full lock, default 45), flip direction, deadzone fix (default 24%).
- Deadzone fix: ETS2/XInput ignores about 24% of stick travel, so the page sends values that start past it.
- Pedals: hold to press, value ramps (throttle up 2.5/s, down 6/s; brake up 4/s, down 8/s), fill bars.
- Safety: pedals, steering and buttons are zeroed/released on disconnect or when the page is hidden.
- Layout (landscape, three columns):
  - Left: Brake pedal.
  - Centre: steering readout and bar; quick row `Left | Horn | Enter | Right` (equal-width buttons via the `.row button.act { flex: 1 1 0; min-width: 0; white-space: nowrap; }` rule); bottom row `Calibrate | Pause | More` (Pause = Esc, centred). `More` opens a panel over the centre with two tabs: **Buttons** (Hazards, Lights, High beam, Wipers, Parking brake, Engine, Trailer; 4-column grid, Trailer spans two cells) and **Settings** (Flip direction, Sensitivity, Deadzone fix).
  - Right: **Cruise** button on top, Throttle pedal below (so cruise can be toggled with the throttle thumb).
- Buttons highlight only while touched; the page does not know the truck's real state (lights, hazards, cruise are toggles in the game).

## What we did, in order
1. Original handoff state: phone page, HTTPS + WebSocket server, virtual gamepad, tilt steering, throttle, brake, connection status.
2. Cloned the repo in the sandbox (web fetch is blocked by GitHub, `git clone` works) and added the button system: `btn` message, `KEYMAP`, pydirectinput key presses, held-key release on disconnect, quick row + More panel (Buttons / Settings tabs).
3. Hazard key changed from F7 to `F` to match his ETS2 bindings.
4. Buttons first did nothing in-game: added `[btn]` console logging, a longer tap (0.12 s) and an error guard. Root cause was privilege levels: PowerShell and ETS2 must both run as Administrator.
5. Added Cruise (`C`) above the Throttle pedal.
6. Added Trailer (`T`) and Enter (`Enter`), then moved Enter into the main quick row and added a centred Pause (`Esc`) button; Trailer stays in More.
7. Enter changed from tap to hold (one word in `KEYMAP`); Left/Right size mismatch fixed with the `.row button.act` CSS rule.
8. Wrote README.md, requirements.txt and .gitignore for the GitHub repo.
9. Wrote `start-server.bat` (self-elevating launcher).
10. Discussed Bluetooth for the occasional ~2 s disconnects: not worth it (a browser page cannot act as a Bluetooth gamepad; it would need a native Android app). Decided to live with the drops for now.

## Gotchas already hit
- A terminal opened as Administrator starts in System32. Work from the project folder (the .bat does this).
- ViGEmBus had to be installed manually from GitHub (nefarius/ViGEmBus), then a restart.
- The venv must be activated in every new terminal (the .bat does this).
- Buttons did nothing until the server and ETS2 were both run as Administrator (UIPI blocks keys from a normal process to an elevated one).
- Hazard key on this setup is `F` (not F7).
- Wipers: the 4th press originally did not switch them off. ETS2 has separate "Wipers" and "Wipers Back" bindings, which was the suspected cause. The user reports it is now resolved; the exact change made was not recorded here.
- pydirectinput only imports on Windows (it uses ctypes.windll), so server.py cannot be run in the Linux sandbox; checks there are limited to compiling and linting.
- Occasional ~2 s WiFi drops while driving. Accepted for now. Ideas if it gets worse: both phone and laptop on 5 GHz (separate SSIDs), laptop WiFi adapter power saving off, USB tethering or Windows Mobile Hotspot, a pong watchdog with faster reconnect (currently server ping interval/timeout ~5 s, phone reconnects after ~1 s), logging disconnect reasons, and a short grace period before zeroing controls.

## Status
Working in ETS2 per the user: connection status, tilt steering, throttle, brake, and all buttons (indicators, hazards, lights, high beam, horn, wipers incl. off, parking brake, engine, cruise, trailer, Enter, pause) with the server and ETS2 both as Administrator. Layout is settled (quick row, Pause centred, equal-size buttons). `start-server.bat` is in place. README.md, requirements.txt and .gitignore are written. The newest buttons were not individually itemised as tested, so re-check cruise, trailer and pause if something seems off.

## What more we can do
1. GitHub housekeeping: add screenshots/GIF in `docs/` (README links `docs/phone-ui.png`), add a LICENSE file, commit `start-server.bat`, `requirements.txt`, `.gitignore`; if `venv/` or `certs/` were ever committed run `git rm -r --cached venv certs`. Consider pinning versions in requirements.txt from `pip freeze`.
2. Live telemetry on the phone (speed, gear, cruise state, lights, wipers level, hazards) with an ETS2 telemetry plugin (e.g. ets2-telemetry-server). This would also let the buttons show the real state instead of just flashing, and fix toggle desync.
3. More buttons: cruise speed +/- (cruise increase/decrease keys), engine brake / retarder up and down, beacon, gear shift hints, camera switch (1 to 6), GPS/route advisor.
4. Accident protection: make Pause (and/or Enter) require a short press-and-hold if stray touches become a problem.
5. Customisable layout: let the phone choose which buttons sit in the quick row; remember the choice in localStorage.
6. Haptics: `navigator.vibrate` on button press (Android Chrome supports it).
7. Light security: any device on the WiFi that opens the page can drive. Add a short PIN or token in the QR code URL checked on the WebSocket.
8. Connection robustness: pong watchdog, faster reconnect, disconnect logging (see Gotchas).
9. Tuning knobs: SMOOTH and DEADZONE in the tilt block, `pedals` rates, `lockDeg` default, tap duration in `handle_button`.
