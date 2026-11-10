# ETS2 Phone Controller: handoff note

Paste this into a new chat (with server.py and static/index.html attached, or the GitHub link) to continue without re-reading the old conversation.

Repo: https://github.com/suryanshsinghrathod35-bit/ETS2-Mobile-Controller (public). Note: the chat's web fetch tool cannot open GitHub (robots.txt), but `git clone` inside the sandbox works, so ask Claude to clone it.

## Goal
Use an Android phone as a wireless controller for Euro Truck Simulator 2 on a Windows 11 laptop: tilt steering, throttle/brake pedals, and buttons (indicators, lights, horn, wipers, cruise control, etc.). ETS2 keybinds are default except where noted below. Home WiFi has 2.4 GHz and 5 GHz; the setup must work on either.

## How to run
```
cd $HOME\Desktop\ets2-controller
venv\Scripts\activate
python server.py        # optional: python server.py <laptop-ip>
```
- **Run PowerShell AND ETS2 both as Administrator** (or both normal). With mixed privilege levels the keyboard buttons do nothing, because Windows blocks a normal process from sending keys to an elevated one. Both as Administrator is what works on this machine.
- A terminal opened as Administrator starts in System32: `cd` to the project folder first, then activate the venv.
- The first Windows Firewall popup needs "Private networks" ticked.
- Scan the QR code on the phone, tap Advanced > Proceed past the self-signed certificate warning, tap "Start driving".
- Editing static/index.html needs only a phone page reload (hard-reload if it looks stale). Editing server.py needs a server restart (Ctrl+C, run again).
- ETS2 must be the focused window for the keyboard buttons to work (the gamepad axes work regardless of focus).

## Folder layout
```
ets2-controller/
  venv/
  server.py
  static/index.html
  certs/            (auto-generated per IP)
  test_pad.py       (old virtual-gamepad test)
  ViGEmBus_1.22.0_x64_x86_arm64.exe   (driver installer, also in the repo)
  HANDOFF.md
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
- `KEYMAP` dict at the top of server.py maps a button id to (key, mode). Mode `tap` = 0.12 s press on touch-down; mode `hold` = key held while the button is held (horn).

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

- Key names are pydirectinput names. Unknown names fail silently.
- Every button press is logged in the server console as `[btn] <id> down -> key '<k>' (<mode>)`. If that line appears but nothing happens in-game, it is a focus/admin/keybind issue; if it does not appear, the phone page is stale.
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
  - Centre: steering readout and bar; quick row `Left | Horn | Right`; `Calibrate` and `More`. `More` opens a panel over the centre with two tabs: **Buttons** (Hazards, Lights, High beam, Wipers, Parking brake, Engine) and **Settings** (Flip direction, Sensitivity, Deadzone fix).
  - Right: **Cruise** button on top, Throttle pedal below (so cruise can be toggled with the throttle thumb).
- Buttons highlight only while touched; the page does not know the truck's real state (lights, hazards, cruise are toggles in the game).

## Gotchas already hit
- A terminal opened as Administrator starts in System32. Work from the Desktop folder.
- ViGEmBus had to be installed manually from GitHub (nefarius/ViGEmBus), then a restart.
- The venv must be activated in every new terminal.
- Buttons did nothing until PowerShell and ETS2 were both run as Administrator (UIPI blocks keys from a normal process to an elevated one).
- Hazard key on this setup is `F` (not F7).
- **Wipers:** ETS2 has two mappings, "Wipers" and "Wipers Back". The default P press should cycle off > 1 > 2 > 3 > off, but on this setup the 4th press did not turn them off. Check Options > Controls > Keyboard for a "Wipers Back" binding: either unassign it (then P alone should cycle through off), or add its key to KEYMAP as an extra button (see next steps).

## Status
Working and tested in ETS2: connection status, tilt steering, throttle, brake, and the keyboard buttons (indicators, hazards, lights, high beam, horn, parking brake, engine) with both PowerShell and ETS2 as Administrator. Wipers cycle 1 to 3 but the 4th press does not switch them off yet (see Gotchas). The Cruise button was added last and is untested.

## What more we can do
1. Fix the wipers-off behaviour: unassign "Wipers Back" in ETS2, or add a `wipers_off` button/key to KEYMAP (and a matching button in the More panel).
2. Double-click launcher (.bat) that starts the server as Administrator: activate the venv, run `python server.py`, and request elevation (e.g. via `powershell Start-Process ... -Verb RunAs`).
3. Live telemetry on the phone (speed, gear, cruise state, lights, wipers level, hazards) with an ETS2 telemetry plugin (e.g. ets2-telemetry-server). This would also let the buttons show the real state instead of just flashing, and fix toggle desync.
4. More buttons: cruise speed +/- (cruise increase/decrease keys), engine brake / retarder up and down, beacon, trailer attach/detach, gear shift hints, camera switch (1 to 6), GPS/route advisor, pause.
5. Customisable layout: let the phone choose which buttons sit in the quick row; remember the choice in localStorage.
6. Haptics: `navigator.vibrate` on button press (Android Chrome supports it).
7. Light security: any device on the WiFi that opens the page can drive. Add a short PIN or token in the QR code URL checked on the WebSocket.
8. Tuning knobs: SMOOTH and DEADZONE in the tilt block, `pedals` rates, `lockDeg` default, tap duration in `handle_button`.
