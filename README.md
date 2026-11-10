# ETS2 Mobile Controller

Use your Android phone as a wireless controller for **Euro Truck Simulator 2** on a Windows laptop: tilt the phone to steer, hold the on-screen pedals to drive, and tap buttons for indicators, lights, horn, wipers and cruise control.

> Not affiliated with or endorsed by SCS Software.

<!-- Add screenshots / a short GIF here, e.g. docs/phone-ui.png and docs/in-game.gif -->
![Phone UI](docs/phone-ui.png)

## Features

- **Tilt steering:** hold the phone like a wheel; adjustable sensitivity, flip direction, one-tap calibration
- **Hold-to-press pedals:** throttle and brake with smooth ramping
- **Buttons:** left/right indicator, horn, hazards, lights, high beam, wipers, parking brake, engine, cruise control, trailer attach/detach, Enter, pause
- **Connection status** on the phone, with live latency
- **Works on 2.4 GHz or 5 GHz WiFi:** the server auto-detects your laptop's IP (or you can pass one)
- **Safe by default:** if the phone disconnects, the page is hidden or fullscreen is left, steering, pedals and held keys are released

## How it works

```
Phone page (HTTPS)  <--  wss://<laptop-ip>:8443/ws  -->  server.py
                                                          |-- steering + pedals -> virtual Xbox 360 gamepad (ViGEmBus + vgamepad) -> ETS2
                                                          '-- buttons           -> keyboard key presses (pydirectinput)         -> ETS2
```

- The page is served over HTTPS (self-signed certificate, generated automatically) because Android Chrome blocks motion sensors on plain HTTP.
- One Python server serves both the page and the WebSocket on port 8443.

## Requirements

- Windows 10/11 laptop running ETS2
- Android phone with Chrome, on the same WiFi network as the laptop
- Python 3 (developed on 3.14)
- [ViGEmBus](https://github.com/nefarius/ViGEmBus) driver (the installer is included in this repo)

## Setup

```powershell
git clone https://github.com/suryanshsinghrathod35-bit/ETS2-Mobile-Controller.git
cd ETS2-Mobile-Controller
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Then run `ViGEmBus_1.22.0_x64_x86_arm64.exe` to install the virtual gamepad driver and **restart your PC**.

## Running

1. Start ETS2 **as Administrator**.
2. Open PowerShell **as Administrator**, go to the project folder (an elevated terminal starts in `System32`), and run:
   ```powershell
   cd path\to\ETS2-Mobile-Controller
   venv\Scripts\activate
   python server.py
   ```
   To force a specific IP (for example a phone hotspot): `python server.py 192.168.1.5`
3. On the first run, Windows Firewall asks for access. Tick **Private networks**.
4. Scan the QR code shown in the terminal with your phone.
5. Chrome shows a certificate warning (expected, the certificate is self-signed). Tap **Advanced > Proceed**.
6. Turn the phone sideways and tap **Start driving**. The current holding angle becomes "straight".
7. Click into the ETS2 window so it has focus.

> **Both ETS2 and PowerShell must run at the same privilege level** (Administrator works). If they differ, Windows blocks the keyboard buttons, while steering and pedals keep working.

## ETS2 setup

Steering and pedals arrive as a virtual Xbox 360 controller:

| Action | Binding |
|---|---|
| Steering | Left stick X axis |
| Acceleration / Braking | Left stick Y axis (the default Y axis) |

The buttons send keyboard keys, so keep the default ETS2 keyboard bindings, or edit `KEYMAP` in `server.py`:

| Button | Key | Mode |
|---|---|---|
| Left indicator | `[` | tap |
| Right indicator | `]` | tap |
| Hazards | `F` | tap |
| Lights | `L` | tap |
| High beam | `K` | tap |
| Horn | `H` | hold |
| Wipers | `P` | tap |
| Parking brake | `Space` | tap |
| Engine | `E` | tap |
| Cruise control | `C` | tap |
| Attach / detach trailer | `T` | tap |
| Enter (tolls, job menu, confirm) | `Enter` | tap |
| Pause menu | `Esc` | tap |

Check your own bindings under **Options > Controls > Keyboard** and change the table in `server.py` if any differ. Key names are [pydirectinput](https://github.com/learncodebygaming/pydirectinput) names (`"["`, `"f"`, `"space"`, ...). Restart the server after editing it.

## Phone controls

- **Centre panel:** steering readout, quick row (Left, Horn, Enter, Right), and a bottom row with Calibrate, **Pause** (Esc) and **More**
- **More > Buttons:** Hazards, Lights, High beam, Wipers, Parking brake, Engine, Trailer
- **More > Settings:** Flip direction, Sensitivity (degrees for full lock), Deadzone fix
- **Right side:** Cruise button above the Throttle pedal
- **Left side:** Brake pedal

Settings are saved on the phone.

### The "Deadzone fix"

ETS2 ignores roughly the first 24% of stick travel, so small tilts would do nothing. The page jumps past that dead region (default 24%). If steering feels twitchy or dead, adjust the slider.

## Troubleshooting

| Problem | Fix |
|---|---|
| Buttons do nothing, but steering and pedals work | Run PowerShell and ETS2 both as Administrator, and click into the ETS2 window. Check the server console for `[btn] ... -> key ...` lines: if they appear, the phone is fine and it is a focus, privilege or keybind issue; if they don't, hard-reload the phone page. |
| Phone can't open the page | Same WiFi as the laptop? Firewall "Private networks" ticked? Try `python server.py <laptop-ip>`. |
| Tilt steering doesn't work | The page must be opened over HTTPS (use the QR code) and motion sensors must be allowed in Chrome. |
| Steering is reversed | More > Settings > Flip direction. |
| Wipers stop at the highest setting | In ETS2 Controls, check the "Wipers Back" binding: unassign it so the Wipers key cycles through off, or bind it to its own key. |
| `ViGEmBus` / gamepad errors | Install the driver from this repo and restart the PC. |
| Certificate warning every time | Normal for a self-signed certificate; tap Advanced > Proceed. A new certificate is created per laptop IP in `certs/`. |

## Security note

There is no login: anyone on your WiFi who opens the page can control the truck (and send the mapped keys to your PC). Use it on a network you trust. A PIN or token in the QR code URL is on the roadmap.

## Project structure

```
server.py            HTTPS + WebSocket server, virtual gamepad, key presses
static/index.html    the phone page (UI, tilt steering, pedals, buttons)
test_pad.py          small virtual-gamepad test
requirements.txt     Python packages
HANDOFF.md           developer notes and next steps
```

## Roadmap

- Live telemetry on the phone (speed, gear, real state of lights, wipers and cruise)
- Cruise speed up/down, retarder, beacon and camera buttons
- Customisable quick-button row
- Vibration feedback on press
- PIN/token for the connection
- Double-click launcher that starts the server as Administrator

## Credits

- [ViGEmBus](https://github.com/nefarius/ViGEmBus) by Nefarius
- [vgamepad](https://github.com/yannbouteiller/vgamepad)
- [websockets](https://github.com/python-websockets/websockets), [pydirectinput](https://github.com/learncodebygaming/pydirectinput), [qrcode](https://github.com/lincolnloop/python-qrcode), [cryptography](https://github.com/pyca/cryptography)

## License

Add a license of your choice (for example MIT) as a `LICENSE` file.
