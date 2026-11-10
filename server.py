"""ETS2 phone controller - Phase 2 server.

Run:  python server.py            (auto-detects your laptop's WiFi IP)
      python server.py 192.168.1.5   (force a specific IP, e.g. hotspot)
"""
import asyncio
import datetime
import ipaddress
import json
import socket
import ssl
import sys
from pathlib import Path

import pydirectinput
import qrcode
import vgamepad as vg
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from websockets.asyncio.server import serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Response

sys.stdout.reconfigure(encoding="utf-8")

PORT = 8443
BASE = Path(__file__).parent
PAGE = BASE / "static" / "index.html"
CERT_DIR = BASE / "certs"

pydirectinput.PAUSE = 0          # no built-in delay after each key call
pydirectinput.FAILSAFE = False   # don't abort when the mouse hits a screen corner

pad = None  # virtual Xbox 360 controller, created in main()
state = {"steer": 0.0, "throttle": 0.0, "brake": 0.0}

# Phone button id -> (keyboard key, mode)
#   "tap"  = quick press-and-release on touch (toggles: lights, indicators, ...)
#   "hold" = key stays down while the button is held (horn)
# These are ETS2's usual default keys. Check them against Options > Controls >
# Keyboard in the game and edit any that differ. Key names are pydirectinput's
# (e.g. "[", "]", "f7", "space", "e").
KEYMAP = {
    "left":     ("[",     "tap"),
    "right":    ("]",     "tap"),
    "hazard":   ("f",     "tap"),
    "lights":   ("l",     "tap"),
    "highbeam": ("k",     "tap"),
    "horn":     ("h",     "hold"),
    "wipers":   ("p",     "tap"),
    "parking":  ("space", "tap"),
    "engine":   ("e",     "tap"),
    "cruise":   ("c",     "tap"),
    "trailer":  ("t",     "tap"),
    "enter":    ("enter", "tap"),
    "pause":    ("esc",   "tap"),
}
held_keys = set()  # keys currently held down by "hold" buttons


async def handle_button(btn_id, down):
    """Translate a phone button event into a real key press for ETS2."""
    entry = KEYMAP.get(btn_id)
    if entry is None:
        print(f"\n   [btn] unknown button id: {btn_id!r}")
        return
    key, mode = entry
    if down or mode == "hold":
        print(f"\n   [btn] {btn_id} {'down' if down else 'up'} -> key {key!r} ({mode})")
    if mode == "hold":
        if down and key not in held_keys:
            held_keys.add(key)
            pydirectinput.keyDown(key)
        elif not down and key in held_keys:
            held_keys.discard(key)
            pydirectinput.keyUp(key)
    elif down:  # tap: act on touch-down only
        pydirectinput.keyDown(key)
        await asyncio.sleep(0.12)  # long enough for the game to see it at low FPS
        pydirectinput.keyUp(key)


def release_all_keys():
    for key in list(held_keys):
        pydirectinput.keyUp(key)
    held_keys.clear()


def apply_state():
    """Push the current controls to the virtual gamepad.

    Left stick X  = steering
    Left stick Y  = throttle (up) minus brake (down)   -> ETS2's default Y axis
    Triggers      = throttle (RT) / brake (LT), kept as an alternative binding
    """
    pad.left_joystick_float(
        x_value_float=state["steer"],
        y_value_float=state["throttle"] - state["brake"],
    )
    pad.right_trigger_float(state["throttle"])
    pad.left_trigger_float(state["brake"])
    pad.update()


def get_local_ip():
    """IP of the network adapter the laptop uses to reach the network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # no packet is actually sent
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def ensure_cert(ip):
    """Create (once per IP) a self-signed certificate valid for this IP."""
    CERT_DIR.mkdir(exist_ok=True)
    tag = ip.replace(".", "-")
    cert_path = CERT_DIR / f"cert-{tag}.pem"
    key_path = CERT_DIR / f"key-{tag}.pem"
    if cert_path.exists() and key_path.exists():
        return cert_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ets2-phone-controller")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.ip_address(ip)), x509.DNSName("localhost")]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


def process_request(connection, request):
    """Plain HTTPS requests get the phone page; /ws continues as WebSocket."""
    if request.path == "/ws":
        return None
    if request.path in ("/", "/index.html"):
        body = PAGE.read_bytes()
        headers = Headers(
            {
                "Content-Type": "text/html; charset=utf-8",
                "Content-Length": str(len(body)),
                "Cache-Control": "no-store",
            }
        )
        return Response(200, "OK", headers, body)
    headers = Headers({"Content-Type": "text/plain", "Content-Length": "9"})
    return Response(404, "Not Found", headers, b"Not found")


async def handler(ws):
    addr = ws.remote_address[0]
    print(f"\n✅ Phone connected ({addr})")
    await ws.send(json.dumps({"t": "hello"}))  # acknowledgement for the phone
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
                kind = msg.get("t")
                if kind == "ping":
                    await ws.send(json.dumps({"t": "pong", "ts": msg.get("ts")}))
                elif kind == "steer":
                    state["steer"] = max(-1.0, min(1.0, float(msg.get("v", 0))))
                    apply_state()
                elif kind == "throttle":
                    state["throttle"] = max(0.0, min(1.0, float(msg.get("v", 0))))
                    apply_state()
                elif kind == "brake":
                    state["brake"] = max(0.0, min(1.0, float(msg.get("v", 0))))
                    apply_state()
                elif kind == "btn":
                    try:
                        await handle_button(str(msg.get("id")), bool(msg.get("down")))
                    except Exception as e:  # never drop the phone because of a key error
                        print(f"\n   [btn] key press failed: {e!r}")
                elif kind == "lat":
                    print(f"\r   latency: {msg.get('ms')} ms   ", end="", flush=True)
            except (ValueError, TypeError):
                continue
    except ConnectionClosed:
        pass
    finally:
        # Safety: never leave the truck steering/accelerating after a drop.
        state.update(steer=0.0, throttle=0.0, brake=0.0)
        release_all_keys()
        pad.reset()
        pad.update()
        print(f"\n❌ Phone disconnected ({addr})")


async def main():
    global pad
    ip = sys.argv[1] if len(sys.argv) > 1 else get_local_ip()
    cert, key = ensure_cert(ip)
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(cert, key)

    pad = vg.VX360Gamepad()
    url = f"https://{ip}:{PORT}"

    print("=" * 50)
    print(" ETS2 phone controller")
    print(f" Open on your phone:  {url}")
    print("=" * 50)
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make()
    qr.print_ascii(invert=True)
    print("Waiting for phone...  (Ctrl+C to stop)")

    async with serve(
        handler,
        "0.0.0.0",
        PORT,
        ssl=ctx,
        process_request=process_request,
        ping_interval=5,
        ping_timeout=5,
    ) as server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
