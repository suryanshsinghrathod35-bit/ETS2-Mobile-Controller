# ETS2 Phone Controller: handoff note

Paste this into a new chat (with server.py and static/index.html attached) to continue without re-reading the old conversation.

## Goal
Use an Android phone as a wireless controller for Euro Truck Simulator 2 on a Windows 11 laptop. Tilt steering, throttle/brake pedals, then buttons (indicators, lights, horn, wipers, etc.). ETS2 keybinds are all default. Home WiFi has 2.4 GHz and 5 GHz; the setup must work on either.

## How to run
```
cd $HOME\Desktop\ets2-controller
venv\Scripts\activate
python server.py        # optional: python server.py <laptop-ip>
```
- Use a normal (non-admin) PowerShell. The first Windows Firewall popup needs "Private networks" ticked.
- Scan the QR code on the phone, tap Advanced > Proceed past the self-signed certificate warning, tap "Start driving".
- Editing static/index.html needs only a phone page reload. Editing server.py needs a server restart.

## Folder layout
```
ets2-controller/
  venv/
  server.py
  static/index.html
  certs/            (auto-generated per IP)
  test_pad.py       (old virtual-gamepad test)
```

## Architecture
Phone page (HTTPS) <-> wss://<laptop-ip>:8443/ws <-> server.py -> vgamepad virtual Xbox 360 controller (ViGEmBus driver) -> ETS2.

- HTTPS is required because Android Chrome blocks motion sensors on plain HTTP.
- server.py serves the page and the WebSocket on one port (websockets library, process_request).
- Python 3.14, packages: vgamepad, websockets, qrcode, pydirectinput, cryptography.

## Message protocol (JSON over WebSocket)
- Server to phone: `hello` (connection acknowledged), `pong` (echoes `ts`).
- Phone to server: `ping {ts}`, `lat {ms}`, `steer {v: -1..1}`, `throttle {v: 0..1}`, `brake {v: 0..1}`.

## Controller mapping (server.py, apply_state)
- Left stick X = steering.
- Left stick Y = throttle minus brake. ETS2 Acceleration/Braking are bound to the default Y axis.
- Triggers also carry throttle (RT) and brake (LT). Binding them in ETS2 did not work well: both triggers appear as one merged Z axis.
- On disconnect the server resets state and the gamepad (safety).

## Phone page features (static/index.html)
- Start screen: fullscreen, landscape lock, wake lock, auto-calibrate. Leaving fullscreen shows it again and releases controls.
- Tilt steering: devicemotion, angle = atan2(gy, gx), minus calibrated offset, smoothed (SMOOTH 0.35), 2 degree deadzone. Clockwise = right.
- Settings saved in localStorage: sensitivity (degrees for full lock, default 45), flip direction, deadzone fix (default 24%).
- Deadzone fix: ETS2/XInput ignores about 24% of stick travel, so the page sends values that start past it.
- Pedals: hold to press, value ramps (throttle up 2.5/s, down 6/s; brake up 4/s, down 8/s), fill bars.
- Safety: pedals and steering are zeroed on disconnect or when the page is hidden.
- Layout (landscape): brake left, centre panel (steering readout, Calibrate, Flip, Sensitivity, Deadzone fix), throttle right.

## Gotchas already hit
- A terminal opened as Administrator starts in System32. Work from the Desktop folder in a normal terminal.
- ViGEmBus had to be installed manually from GitHub (nefarius/ViGEmBus), then a restart.
- The venv must be activated in every new terminal.

## Status
Working and tested in ETS2: connection status (phone and server), tilt steering, throttle, brake.

## Next steps
1. Buttons: left/right indicator, hazards, headlights, high beam, horn, wipers, parking brake, engine. Send as key presses with pydirectinput (scan codes), reading the exact default keys from ETS2's Controls menu. Layout still undecided: strip in the centre panel or a slide-out panel.
2. Double-click launcher (.bat) to start the server.
3. Optional: live speed/gear display on the phone via an ETS2 telemetry plugin.
4. Tuning knobs: SMOOTH and DEADZONE in the tilt block, `pedals` rates, `lockDeg` default.
