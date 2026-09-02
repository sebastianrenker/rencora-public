"""
dashboard/server.py — JARVIS Local HTTP Dashboard

Plain HTTP on port 8000 (no SSL warnings, no firewall issues).
Security at the application layer: AES-256-CBC with session-key-derived key.
CryptoJS is auto-downloaded once and served locally — no CDN needed after that.

Install deps:  pip install fastapi "uvicorn[standard]" cryptography
"""

import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import socket
import string
import time
from pathlib import Path

_DEPS_OK = False
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    import uvicorn
    _DEPS_OK = True
except ImportError:
    pass

# python-multipart is required for file uploads — optional dependency
_UPLOAD_OK = False
try:
    from fastapi import UploadFile, File as FastAPIFile
    _UPLOAD_OK = True
except Exception:
    pass

BASE_DIR    = Path(__file__).resolve().parent.parent
STATIC_DIR  = Path(__file__).parent / "static"
PORT        = 8000
MAX_UPLOAD_MB = 500


def _make_uploads_dir() -> Path:
    """Return (and create) the cross-platform uploads folder."""
    for candidate in [
        Path.home() / "Downloads" / "JARVIS Uploads",
        Path.home() / "Documents" / "JARVIS Uploads",
        BASE_DIR / "uploads",
    ]:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            pass
    return BASE_DIR / "uploads"


UPLOADS_DIR = _make_uploads_dir()

def _get_gemini_key() -> str | None:
    try:
        import json as _json
        with open(BASE_DIR / "config" / "api_keys.json", "r", encoding="utf-8") as f:
            return _json.load(f).get("gemini_api_key")
    except Exception:
        return None

_KEY_CHARS = [c for c in (string.ascii_uppercase + string.digits)
              if c not in ('O', 'I', 'L', '0', '1')]

# ── AES-256-CBC ───────────────────────────────────────────────────────────────
_AES_SALT = b'JARVIS-DASHBOARD-v1'


def _derive_key(session_key: str) -> bytes:
    """SHA-256(sessionKey‖salt) → 32-byte AES-256 key (microseconds, no PBKDF2 needed)."""
    return hashlib.sha256(session_key.encode('utf-8') + _AES_SALT).digest()


def _decrypt_cbc(aes_key: bytes, enc_b64: str) -> str:
    """Decrypt base64(IV[16] ‖ ciphertext) with AES-256-CBC + PKCS7."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_pad
    raw      = base64.b64decode(enc_b64)
    iv, ct   = raw[:16], raw[16:]
    dec      = Cipher(algorithms.AES(aes_key), modes.CBC(iv)).decryptor()
    padded   = dec.update(ct) + dec.finalize()
    unpadder = sym_pad.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode('utf-8')


# ── CryptoJS (auto-download once, served locally) ─────────────────────────────
_CRYPTOJS_CDN  = ("https://cdnjs.cloudflare.com/ajax/libs/"
                  "crypto-js/4.2.0/crypto-js.min.js")
_CRYPTOJS_FILE = STATIC_DIR / "crypto-js.min.js"


def _ensure_network_access(port: int) -> None:
    """Cross-platform, best-effort: open port in the OS firewall for LAN access.

    Runs in a background thread — never blocks uvicorn startup.

    Windows : writes a .bat file, runs it elevated via Windows ShellExecuteW
              (native UAC dialog, guaranteed to appear). One-time setup.
    macOS   : osascript admin dialog if the Application Firewall is on.
    Linux   : pkexec GUI → sudo -n → prints manual command as fallback.
    """
    import sys, subprocess, os, tempfile, threading

    # ── Windows ──────────────────────────────────────────────────────────────
    if sys.platform == "win32":
        import ctypes, time

        port_rule = f"JARVIS Dashboard Port {port}"
        prog_rule  = "JARVIS Dashboard Python"
        py_exe     = sys.executable

        def _netsh_rule_exists(name: str) -> bool:
            try:
                r = subprocess.run(
                    ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name}"],
                    capture_output=True, text=True, timeout=5,
                )
                return r.returncode == 0 and "No rules match" not in r.stdout
            except Exception:
                return False

        def _network_is_public() -> bool:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     "(Get-NetConnectionProfile | "
                     "Where-Object {$_.NetworkCategory -eq 'Public'} | "
                     "Measure-Object).Count"],
                    capture_output=True, text=True, timeout=6,
                )
                return r.stdout.strip() not in ("", "0")
            except Exception:
                return False

        need_port    = not _netsh_rule_exists(port_rule)
        need_prog    = not _netsh_rule_exists(prog_rule)
        need_private = _network_is_public()

        if not need_port and not need_prog and not need_private:
            return  # already fully configured

        # Build a .bat file — netsh + powershell, runs fast when elevated
        bat_lines = ["@echo off"]
        if need_private:
            bat_lines.append(
                'powershell -NoProfile -NonInteractive -Command "'
                'Get-NetConnectionProfile | '
                "Where-Object {$_.NetworkCategory -eq 'Public'} | "
                'Set-NetConnectionProfile -NetworkCategory Private"'
            )
        if need_port:
            bat_lines.append(
                f'netsh advfirewall firewall add rule '
                f'name="{port_rule}" protocol=TCP dir=in '
                f'localport={port} action=allow'
            )
        if need_prog:
            bat_lines.append(
                f'netsh advfirewall firewall add rule '
                f'name="{prog_rule}" dir=in action=allow '
                f'program="{py_exe}" enable=yes'
            )

        bat_body = "\r\n".join(bat_lines) + "\r\n"
        fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="jarvis_fw_")
        try:
            os.write(fd, bat_body.encode("mbcs"))   # Windows cmd.exe expects ANSI
            os.close(fd)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            return

        # ── Try running directly (succeeds when already admin) ────────────────
        try:
            r = subprocess.run(
                [bat_path], capture_output=True, timeout=8, shell=True
            )
            if r.returncode == 0:
                print(f"[Dashboard] Firewall configured for port {port}.")
                try:
                    os.unlink(bat_path)
                except Exception:
                    pass
                return
        except Exception:
            pass

        # ── ShellExecuteW: native UAC elevation (most reliable on Windows) ────
        # ShellExecuteW with verb "runas" always shows the UAC dialog regardless
        # of UAC level settings. Non-blocking — uvicorn is already running.
        print("[Dashboard] One-time network setup required.")
        print("[Dashboard] >>> A Windows security dialog will appear — click 'Yes' <<<")
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,       # hwnd  (no parent window)
                "runas",    # verb  (request elevation)
                bat_path,   # file  (our .bat)
                None,       # params
                None,       # working dir
                0,          # SW_HIDE (run without a visible cmd window)
            )
            if int(ret) > 32:
                # ShellExecuteW returns immediately; bat finishes in ~1 second.
                # Sleep briefly so the rules are in place before the first retry.
                time.sleep(2)
                print(f"[Dashboard] Network setup complete — port {port} is open.")
                print("[Dashboard] Refresh your phone browser to connect.")
            else:
                print("[Dashboard] Setup was not allowed.")
                print("[Dashboard] Phone connections may fail until JARVIS is run as Administrator.")
        except Exception as e:
            print(f"[Dashboard] Firewall setup error: {e}")
        finally:
            # Cleanup after the bat has had time to run
            def _cleanup(path: str) -> None:
                time.sleep(5)
                try:
                    os.unlink(path)
                except Exception:
                    pass
            threading.Thread(target=_cleanup, args=(bat_path,), daemon=True).start()
        return

    # ── macOS ─────────────────────────────────────────────────────────────────
    if sys.platform == "darwin":
        fw_ctl = "/usr/libexec/ApplicationFirewall/socketfilterfw"
        try:
            r = subprocess.run(
                [fw_ctl, "--getglobalstate"], capture_output=True, text=True, timeout=5,
            )
            if "disabled" in r.stdout.lower():
                return  # firewall off — nothing to do

            py = sys.executable
            listed = subprocess.run(
                [fw_ctl, "--listapps"], capture_output=True, text=True, timeout=5,
            )
            if py in listed.stdout:
                return  # already allowed

            print("[Dashboard] One-time network setup — enter your password in the macOS dialog.")
            subprocess.run(
                ["osascript", "-e",
                 f'do shell script "{fw_ctl} --add {py} && {fw_ctl} --unblockapp {py}"'
                 f' with administrator privileges'],
                timeout=60,
            )
        except Exception:
            pass  # macOS firewall is off by default — silent failure is fine
        return

    # ── Linux ─────────────────────────────────────────────────────────────────
    def _privileged(cmd: list[str]) -> bool:
        for prefix in (["pkexec"], ["sudo", "-n"]):
            try:
                r = subprocess.run(prefix + cmd, capture_output=True, timeout=30)
                if r.returncode == 0:
                    return True
            except Exception:
                pass
        return False

    try:  # ufw
        r = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=5)
        if "active" in r.stdout.lower():
            if _privileged(["ufw", "allow", f"{port}/tcp"]):
                print(f"[Dashboard] ufw: port {port} allowed.")
            else:
                print(f"[Dashboard] Run manually:  sudo ufw allow {port}/tcp")
            return
    except FileNotFoundError:
        pass

    try:  # firewalld
        r = subprocess.run(
            ["firewall-cmd", "--state"], capture_output=True, text=True, timeout=5,
        )
        if "running" in r.stdout.lower():
            ok = (_privileged(["firewall-cmd", "--add-port", f"{port}/tcp", "--permanent"])
                  and _privileged(["firewall-cmd", "--reload"]))
            if ok:
                print(f"[Dashboard] firewalld: port {port} allowed.")
            else:
                print(f"[Dashboard] Run manually:  sudo firewall-cmd --add-port={port}/tcp --permanent && sudo firewall-cmd --reload")
            return
    except FileNotFoundError:
        pass

    try:  # iptables (not persistent but works until reboot)
        r = subprocess.run(["iptables", "-L", "INPUT", "-n"], capture_output=True, timeout=5)
        if r.returncode == 0:
            if _privileged(["iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"]):
                print(f"[Dashboard] iptables: port {port} opened.")
            else:
                print(f"[Dashboard] Run manually:  sudo iptables -A INPUT -p tcp --dport {port} -j ACCEPT")
    except FileNotFoundError:
        pass  # no iptables means firewall is probably off — nothing to do


def _ensure_crypto_js() -> None:
    if _CRYPTOJS_FILE.exists():
        return
    try:
        import urllib.request
        print("[Dashboard] Downloading CryptoJS (one-time setup)…")
        urllib.request.urlretrieve(_CRYPTOJS_CDN, str(_CRYPTOJS_FILE))
        print("[Dashboard] CryptoJS cached — will serve locally from now on.")
    except Exception as e:
        print(f"[Dashboard] CryptoJS download failed: {e}")
        print(f"[Dashboard] Encryption will fall back to CDN load on client.")


_ensure_crypto_js()


# ── helpers ───────────────────────────────────────────────────────────────────

def _local_ip() -> str:
    """Return the best LAN-facing IPv4 address, no internet required."""
    # Method 1: route trick (fast, works when internet is available)
    for probe in ("8.8.8.8", "1.1.1.1", "192.168.1.1"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect((probe, 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith("127."):
                return ip
        except Exception:
            pass

    # Method 2: hostname resolution (works offline on most systems)
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # Method 3: enumerate all interfaces (fully offline, no external deps)
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def _ensure_certs() -> bool:
    """
    Make sure config/certs holds a TLS key pair, generating a self-signed one the
    first time the dashboard runs.

    The pair is deliberately NOT shipped in the repository. A private key that
    every user downloads is the same as having no private key at all: anyone can
    present a certificate that matches it. Generating locally gives each install
    its own key, costs about a second, and happens exactly once.

    Returns True when a usable pair exists afterwards; False leaves the caller on
    plain HTTP, which still works — the QR code simply encodes http:// instead.
    """
    certs = BASE_DIR / "config" / "certs"
    key_p = certs / "jarvis.key"
    crt_p = certs / "jarvis.crt"
    if key_p.exists() and crt_p.exists():
        return True

    try:
        import datetime
        import ipaddress
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("[Dashboard] cryptography not installed — serving over plain HTTP.")
        print("[Dashboard] For HTTPS run:  pip install cryptography")
        return False

    try:
        certs.mkdir(parents=True, exist_ok=True)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        who = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "JARVIS Dashboard"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JARVIS"),
        ])

        # The SAN has to cover every address the phone might use: the LAN IP the
        # QR code encodes, plus localhost when testing on the machine itself.
        alt = [x509.DNSName("localhost"),
               x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]
        try:
            lan = _local_ip()
            if not lan.startswith("127."):
                alt.append(x509.IPAddress(ipaddress.IPv4Address(lan)))
        except Exception:
            pass          # no LAN address resolvable — localhost entries still work

        # Timezone-aware UTC: datetime.utcnow() is deprecated from Python 3.12 on,
        # and the builder normalises aware values to UTC itself.
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(who)
            .issuer_name(who)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(alt), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )

        key_p.write_bytes(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        crt_p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        try:
            import os as _os
            _os.chmod(key_p, 0o600)   # best effort — largely a no-op on Windows
        except Exception:
            pass

        print(f"[Dashboard] Generated a self-signed certificate for this machine: {certs}")
        return True
    except Exception as e:
        print(f"[Dashboard] Certificate generation failed ({e}) — serving over plain HTTP.")
        return False


def _read(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


# ── DashboardServer ───────────────────────────────────────────────────────────

class DashboardServer:

    def __init__(self):
        self._ip                          = _local_ip()
        self._tokens: set[str]            = set()
        self._display_tokens: set[str]    = set()   # read-only tokens (TV/HUD): receive, cannot command
        self._token_keys: dict[str, str]  = {}   # auth_token → session_key
        self._aes_cache:  dict[str, bytes]= {}   # session_key → AES bytes
        self._clients: set[WebSocket]     = set()
        self._history: list[dict]         = []
        self._command_queue               = asyncio.Queue()
        self._wake_callback               = None
        self._listen_mode_callback        = None
        self._connect_callback            = None
        self._pending_keys: dict[str, float] = {}
        self._device_sessions: dict[str, dict] = {}  # device_token → {session_key}
        self._phone_audio_queue: asyncio.Queue    = asyncio.Queue(maxsize=200)
        self._uploads_dir                 = UPLOADS_DIR
        self._login_html                  = _read("login.html")
        self._app_html                    = _read("app.html")
        self._holo_html                   = _read("rencora.html")   # Rencora holographic UI (2D)
        self._holo3d_html                 = _read("rencora3d.html") # Rencora 3D hand-control UI
        self._desk_html                   = _read("desk.html")     # Rencora desk surface (Phase 1 calibration)
        self._stage_html                  = _read("stage.html")    # Rencora stage / big-screen display (Phase 2)
        self._home_html                   = _read("home.html")     # Rencora home / launcher (Phase 5)
        self._wall_html                   = _read("wall.html")     # Rencora Info-Wall (Wetter/News/Karte)
        self._globe_html                  = _read("globe.html")    # Rencora 3D-Satellitenglobus
        self._status_html                 = _read("status.html")   # Rencora System-Status / Diagnose
        self._lab_html                    = _read("lab.html")       # Rencora Objekt-Labor (Kamera-Scanner)
        self._setup_html                  = _read("setup.html")    # first-run setup (key + name)
        self._tv_html                     = _read("tv.html")       # Fire-TV / 10-foot HUD (read-only)
        self._advisor_html                = _read("advisor.html")  # document advisor HUD
        self._brain_html                  = _read("brain.html")    # Brain neural-graph HUD
        self._remote_html                 = _read("remote.html")   # phone/PC remote control
        self._settings_html               = _read("settings.html") # central settings
        self.app                          = self._build_app()

    # ── one-time key management ───────────────────────────────────────────

    def new_key(self, expiry_secs: int = 600) -> str:
        now = time.time()
        self._pending_keys = {k: v for k, v in self._pending_keys.items() if v > now}
        key = ''.join(secrets.choice(_KEY_CHARS) for _ in range(6))
        self._pending_keys[key] = now + expiry_secs
        return key

    @staticmethod
    def _ssl_enabled() -> bool:
        # Local Rencora mode: plain HTTP on localhost (a secure context — camera/mic
        # still work — with no self-signed-cert warning). Set by run_headless --local.
        if os.environ.get("RENCORA_NO_SSL") == "1":
            return False
        certs = BASE_DIR / "config" / "certs"
        return (certs / "jarvis.key").exists() and (certs / "jarvis.crt").exists()

    def get_url(self) -> str:
        proto = "https" if self._ssl_enabled() else "http"
        return f"{proto}://{self._ip}:{PORT}"

    def get_manual_url(self) -> str:
        """URL for manual browser entry. When HTTPS active, points to alias port (also HTTPS)."""
        if self._ssl_enabled():
            return f"{self._ip}:{PORT + 1}"
        return f"{self._ip}:{PORT}"

    def _aes_key(self, session_key: str) -> bytes:
        if session_key not in self._aes_cache:
            self._aes_cache[session_key] = _derive_key(session_key)
        return self._aes_cache[session_key]

    def _decrypt(self, token: str, enc_b64: str) -> str | None:
        sk = self._token_keys.get(token)
        if not sk:
            return None
        try:
            return _decrypt_cbc(self._aes_key(sk), enc_b64)
        except Exception:
            return None

    # ── callbacks ────────────────────────────────────────────────────────

    def set_wake_callback(self, fn) -> None:
        self._wake_callback = fn

    def set_listen_mode_callback(self, fn) -> None:
        self._listen_mode_callback = fn

    def set_connect_callback(self, fn) -> None:
        self._connect_callback = fn

    # ── broadcast ────────────────────────────────────────────────────────

    async def broadcast(self, msg: dict) -> None:
        self._history.append(msg)
        if len(self._history) > 300:
            self._history = self._history[-300:]
        dead: set[WebSocket] = set()
        for ws in list(self._clients):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    # ── FastAPI app ───────────────────────────────────────────────────────

    def _build_app(self) -> "FastAPI":
        app = FastAPI(docs_url=None, redoc_url=None)

        def _auth(req: Request) -> bool:
            tok = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            return bool(tok) and tok in self._tokens

        # serve CryptoJS from local cache, fallback to CDN redirect
        @app.get("/static/crypto.js")
        async def serve_crypto():
            if _CRYPTOJS_FILE.exists():
                return FileResponse(str(_CRYPTOJS_FILE),
                                    media_type="application/javascript")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(_CRYPTOJS_CDN)

        # shared Rencora<->Jarvis identity switcher (name + accent), used by all surfaces
        @app.get("/static/identity.js")
        async def serve_identity():
            return FileResponse(str(STATIC_DIR / "identity.js"),
                                media_type="application/javascript")

        @app.get("/static/boot.js")
        async def serve_boot():
            return FileResponse(str(STATIC_DIR / "boot.js"),
                                media_type="application/javascript")

        @app.get("/static/vision.js")
        async def serve_vision_js():
            return FileResponse(str(STATIC_DIR / "vision.js"),
                                media_type="application/javascript")

        @app.get("/static/widgets.js")
        async def serve_widgets_js():
            return FileResponse(str(STATIC_DIR / "widgets.js"),
                                media_type="application/javascript")

        @app.get("/static/radial.js")
        async def serve_radial_js():
            return FileResponse(str(STATIC_DIR / "radial.js"),
                                media_type="application/javascript")

        @app.get("/static/nowplaying.js")
        async def serve_nowplaying_js():
            return FileResponse(str(STATIC_DIR / "nowplaying.js"),
                                media_type="application/javascript")

        @app.get("/static/face.js")
        async def serve_face_js():
            return FileResponse(str(STATIC_DIR / "face.js"),
                                media_type="application/javascript")

        # camera pages push their current webcam frame here so voice 'was siehst du' has a recent image
        @app.post("/api/vision-frame")
        async def vision_frame(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                body = await request.json()
                from actions.vision import decode_dataurl, save_frame
                img = decode_dataurl(body.get("image", ""))
                if img:
                    save_frame(img)
                return JSONResponse({"ok": bool(img)})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        # SCAN / 'was siehst du': describe the given frame (or the last cached one) via Gemini vision
        @app.post("/api/vision")
        async def vision_describe(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                body = await request.json()
                q = (body.get("question") or "").strip()
                from actions.vision import decode_dataurl, save_frame, describe_image, describe_latest
                img = decode_dataurl(body.get("image", ""))
                if img:
                    save_frame(img)
                    text = await asyncio.to_thread(describe_image, img, q)
                else:
                    text = await asyncio.to_thread(describe_latest, q)
                return JSONResponse({"text": text or "Kein Kamerabild verfügbar."})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.get("/login", response_class=HTMLResponse)
        async def login_page():
            return HTMLResponse(self._login_html)

        @app.get("/")
        async def index():
            from fastapi.responses import RedirectResponse
            return RedirectResponse("/home")            # Rencora launcher is the start page

        @app.get("/app", response_class=HTMLResponse)
        async def legacy_app():
            html = (self._app_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.get("/holo", response_class=HTMLResponse)
        async def holo():
            # Rencora holographic + hand-gesture interface. Auth handled client-side
            # via sessionStorage bearer token (same as index).
            html = (self._holo_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.get("/holo3d", response_class=HTMLResponse)
        async def holo3d():
            html = (self._holo3d_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.get("/desk", response_class=HTMLResponse)
        async def desk():
            html = (self._desk_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.get("/stage", response_class=HTMLResponse)
        async def stage():
            html = (self._stage_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.get("/home", response_class=HTMLResponse)
        async def home():
            html = (self._home_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.get("/wall", response_class=HTMLResponse)
        async def wall():
            html = (self._wall_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.get("/globe", response_class=HTMLResponse)
        async def globe():
            html = (self._globe_html
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.get("/status", response_class=HTMLResponse)
        async def status_page():
            return HTMLResponse(self._status_html)

        @app.get("/lab", response_class=HTMLResponse)
        async def lab_page():
            return HTMLResponse(self._lab_html)

        @app.get("/api/weather")
        async def api_weather(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                from actions.wall_data import weather
                return JSONResponse(await asyncio.to_thread(weather))
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=502)

        @app.get("/api/news")
        async def api_news(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                from actions.wall_data import news
                return JSONResponse({"items": await asyncio.to_thread(news)})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=502)

        @app.get("/api/summarize")
        async def api_summarize(request: Request, url: str = ""):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            if not url:
                return JSONResponse({"summary": ""})
            try:
                import re as _re
                from actions.wall_data import _get_text
                html = await asyncio.to_thread(_get_text, url)
                html = _re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
                text = _re.sub(r"(?s)<[^>]+>", " ", html)
                text = _re.sub(r"\s+", " ", text).strip()[:6000]
                if not text:
                    return JSONResponse({"summary": ""})
                from plugins.grok import grok_complete
                s = await asyncio.to_thread(
                    grok_complete,
                    "Fasse den folgenden Artikeltext in genau 3 kurzen, klaren deutschen Sätzen "
                    "zusammen. Gib NUR die Zusammenfassung aus:\n\n" + text,
                    "Du fasst Nachrichtenartikel knapp und sachlich zusammen.")
                return JSONResponse({"summary": (s or "").strip()})
            except Exception as e:
                return JSONResponse({"summary": "", "error": str(e)})

        @app.post("/api/lab-detect")
        async def api_lab_detect(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                body = await request.json()
                from actions.lab import save_labels
                save_labels(body.get("labels") or [])
                return JSONResponse({"ok": True})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.post("/api/lab-analyze")
        async def api_lab_analyze(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                body = await request.json()
                from actions.lab import analyze
                labels = body.get("labels") or []
                mode = body.get("mode") or "identify"
                text = await asyncio.to_thread(analyze, labels, mode)
                return JSONResponse({"text": text or ""})
            except Exception as e:
                return JSONResponse({"text": "", "error": str(e)}, status_code=500)

        @app.get("/static/objlab.js")
        async def serve_objlab_js():
            return FileResponse(str(STATIC_DIR / "objlab.js"),
                                media_type="application/javascript")

        @app.get("/api/globe-config")
        async def api_globe_config(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                import json as _json
                p = STATIC_DIR.parent.parent / "config" / "globe.json"
                tok = ""
                if p.exists():
                    tok = (_json.loads(p.read_text(encoding="utf-8")).get("cesium_ion_token") or "").strip()
                return JSONResponse({"ion_token": tok})
            except Exception:
                return JSONResponse({"ion_token": ""})

        @app.get("/api/crypto")
        async def api_crypto(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                import urllib.parse
                from actions.wall_data import _get_json, _cfg as _wcfg
                coins = _wcfg().get("coins") or ["bitcoin", "ethereum", "solana"]
                url = ("https://api.coingecko.com/api/v3/simple/price?ids=" +
                       urllib.parse.quote(",".join(coins)) + "&vs_currencies=eur&include_24hr_change=true")
                data = await asyncio.to_thread(_get_json, url)
                return JSONResponse({"coins": data})
            except Exception as e:
                return JSONResponse({"coins": {}, "error": str(e)})

        _TASKS_FILE = STATIC_DIR.parent.parent / "config" / "wall_tasks.json"

        def _load_tasks():
            try:
                import json as _j
                return _j.loads(_TASKS_FILE.read_text(encoding="utf-8")).get("tasks", [])
            except Exception:
                return []

        def _save_tasks(tasks):
            import json as _j
            try:
                _TASKS_FILE.write_text(_j.dumps({"tasks": tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        @app.get("/api/tasks")
        async def api_tasks_get(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            return JSONResponse({"tasks": _load_tasks()})

        @app.post("/api/tasks")
        async def api_tasks_post(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                body = await request.json()
            except Exception:
                body = {}
            op = (body.get("op") or "add").strip().lower()
            tasks = _load_tasks()
            if op == "add" and (body.get("text") or "").strip():
                tasks.append({"text": body["text"].strip(), "done": False})
            elif op == "toggle":
                i = int(body.get("index", -1))
                if 0 <= i < len(tasks):
                    tasks[i]["done"] = not tasks[i].get("done")
            elif op == "delete":
                i = int(body.get("index", -1))
                if 0 <= i < len(tasks):
                    tasks.pop(i)
            _save_tasks(tasks)
            return JSONResponse({"tasks": tasks})

        @app.get("/api/status")
        async def api_status(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            import json as _j
            base = STATIC_DIR.parent.parent
            gemini = False
            try:
                gemini = bool(_j.loads((base / "config" / "api_keys.json").read_text(encoding="utf-8")).get("gemini_api_key"))
            except Exception:
                pass
            groq_on, provider = False, ""
            try:
                from plugins.grok import is_configured, _provider
                groq_on = is_configured()
                if groq_on:
                    provider = _provider()[3]
            except Exception:
                pass
            wifi_state = "?"
            try:
                from plugins.wifi import _probe
                wifi_state = (await asyncio.to_thread(_probe))[0]
            except Exception:
                pass
            plug = 0
            try:
                plug = len([p for p in (base / "plugins").glob("*.py") if not p.name.startswith("_")])
            except Exception:
                pass
            owner = ""
            try:
                owner = (_j.loads((base / "config" / "owner.json").read_text(encoding="utf-8")).get("name") or "").split()[0]
            except Exception:
                pass
            return JSONResponse({"gemini": gemini, "groq": groq_on, "provider": provider,
                                 "wifi": wifi_state, "plugins": plug, "owner": owner})

        @app.get("/api/flights")
        async def api_flights(request: Request, lat: float = 50.55, lon: float = 9.68):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                from actions.wall_data import _get_json
                d = 2.0
                url = ("https://opensky-network.org/api/states/all?lamin=%s&lomin=%s&lamax=%s&lomax=%s"
                       % (lat - d, lon - d, lat + d, lon + d))
                data = await asyncio.to_thread(_get_json, url)
                out = []
                for s in (data.get("states") or [])[:40]:
                    if s[5] is not None and s[6] is not None:
                        out.append({"lon": s[5], "lat": s[6], "call": (s[1] or "").strip(),
                                    "alt": s[7] or s[13] or 0, "hdg": s[10] or 0})
                return JSONResponse({"flights": out})
            except Exception as e:
                return JSONResponse({"flights": [], "error": str(e)})

        @app.get("/api/nowplaying")
        async def api_nowplaying(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                import plugins.music as m
                p = m._player()
                return JSONResponse({"playing": bool(p.running and p.current_title),
                                     "title": p.current_title or "", "mood": p.mood or "",
                                     "volume": getattr(p, "volume", 70)})
            except Exception as e:
                return JSONResponse({"playing": False, "error": str(e)})

        @app.post("/api/music-control")
        async def api_music_control(request: Request):
            if not _local(request):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            try:
                body = await request.json()
            except Exception:
                body = {}
            action = (body.get("action") or "status").strip().lower()
            try:
                import plugins.music as m
                out = await asyncio.to_thread(
                    m.run, {"action": action, "query": body.get("query", ""),
                            "level": body.get("level", 70)})
                return JSONResponse({"ok": True, "msg": out})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.get("/api/models")
        async def list_models():
            # Drop-in 3D models: any .glb/.gltf in dashboard/static/models/
            mdir = STATIC_DIR / "models"
            out = []
            try:
                for f in sorted(mdir.iterdir()):
                    if f.is_file() and f.suffix.lower() in (".glb", ".gltf"):
                        out.append({"name": f.stem, "file": f.name,
                                    "url": "/models/" + f.name})
            except Exception:
                pass
            return JSONResponse(out)

        @app.get("/models/{filename}")
        async def get_model(filename: str):
            name = Path(filename).name                     # strip any path components
            if Path(name).suffix.lower() not in (".glb", ".gltf", ".bin", ".png", ".jpg", ".jpeg"):
                return JSONResponse({"error": "unsupported"}, status_code=404)
            path = STATIC_DIR / "models" / name
            if not path.exists():
                return JSONResponse({"error": "not found"}, status_code=404)
            return FileResponse(str(path), filename=name)

        @app.get("/setup", response_class=HTMLResponse)
        async def setup_page():
            return HTMLResponse(self._setup_html)

        @app.get("/advisor", response_class=HTMLResponse)
        async def advisor_page():
            return HTMLResponse(self._advisor_html)

        @app.get("/remote", response_class=HTMLResponse)
        async def remote_page():
            return HTMLResponse(self._remote_html)

        @app.get("/settings", response_class=HTMLResponse)
        async def settings_page():
            return HTMLResponse(self._settings_html)

        @app.get("/manifest.json")
        async def pwa_manifest():
            icon = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='192' "
                    "height='192'><rect width='192' height='192' rx='36' fill='%2304070e'/><circle "
                    "cx='96' cy='96' r='62' fill='none' stroke='%23b06bff' stroke-width='10'/><circle "
                    "cx='96' cy='96' r='20' fill='%2338e6ff'/></svg>")
            return JSONResponse({
                "name": "Rencora Fernbedienung", "short_name": "Rencora",
                "start_url": "/remote", "scope": "/", "display": "standalone",
                "background_color": "#04070e", "theme_color": "#04070e",
                "icons": [{"src": icon, "sizes": "192x192", "type": "image/svg+xml", "purpose": "any"},
                          {"src": icon, "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"}]})

        @app.get("/sw.js")
        async def pwa_sw():
            from fastapi.responses import Response
            js = ("self.addEventListener('install',e=>self.skipWaiting());"
                  "self.addEventListener('activate',e=>self.clients.claim());"
                  "self.addEventListener('fetch',e=>{});")
            return Response(js, media_type="application/javascript")

        @app.get("/api/settings-status")
        async def settings_status(request: Request):
            if not _local(request):
                return JSONResponse({"error": "local only"}, status_code=403)
            cdir = BASE_DIR / "config"
            def _j(name):
                try:
                    return json.loads((cdir / name).read_text(encoding="utf-8"))
                except Exception:
                    return {}
            grok = _j("grok.json"); bambu = (_j("printer.json").get("bambu") or {})
            try:
                interests = _j("interests.json").get("topics", [])
            except Exception:
                interests = []
            try:
                brain = _brain_mod().stats()
            except Exception:
                brain = {}
            return JSONResponse({
                "grok_set": bool(grok.get("xai_api_key")),
                "bambu_set": bool(bambu.get("host") and bambu.get("serial") and bambu.get("access_code")),
                "interests": interests, "brain": brain})

        @app.post("/api/settings-save")
        async def settings_save(request: Request):
            if not _local(request):
                return JSONResponse({"ok": False, "error": "Nur auf deinen Geräten."}, status_code=403)
            try:
                body = await request.json()
            except Exception:
                return JSONResponse({"ok": False, "error": "Ungültige Daten."}, status_code=400)
            cdir = BASE_DIR / "config"
            def _load(name):
                try:
                    return json.loads((cdir / name).read_text(encoding="utf-8"))
                except Exception:
                    return {}
            def _write(name, data):
                (cdir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                if body.get("grok_key"):
                    g = _load("grok.json"); g["xai_api_key"] = body["grok_key"].strip(); g.setdefault("model", "grok-4")
                    _write("grok.json", g)
                if body.get("bambu"):
                    p = _load("printer.json"); p["bambu"] = body["bambu"]; _write("printer.json", p)
                if body.get("add_interest") or body.get("remove_interest"):
                    d = _load("interests.json"); topics = d.get("topics", []) if isinstance(d, dict) else []
                    add = (body.get("add_interest") or "").strip()
                    rem = (body.get("remove_interest") or "").strip()
                    if add and add.lower() not in [t.lower() for t in topics]:
                        topics.append(add)
                    if rem:
                        topics = [t for t in topics if t.lower() != rem.lower()]
                    _write("interests.json", {"topics": topics})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
            return JSONResponse({"ok": True})

        @app.get("/brain", response_class=HTMLResponse)
        async def brain_page():
            return HTMLResponse(self._brain_html)

        def _local(request: Request) -> bool:
            # Trusted = this machine OR the user's own Tailscale network (100.64.0.0/10).
            # Tailscale is a private VPN of only the user's own devices, so their phone
            # counts as trusted from anywhere; strangers on the internet do not.
            h = request.client.host if request.client else ""
            if h in ("127.0.0.1", "::1", "localhost"):
                return True
            p = h.split(".")
            if len(p) == 4 and p[0] == "100":
                try:
                    return 64 <= int(p[1]) <= 127
                except Exception:
                    return False
            return False

        def _brain_mod():
            import sys as _sys
            if str(BASE_DIR) not in _sys.path:
                _sys.path.insert(0, str(BASE_DIR))
            import brain_db
            return brain_db

        @app.post("/api/brain/scan")
        async def brain_scan(request: Request):
            if not _local(request):
                return JSONResponse({"error": "local only"}, status_code=403)
            try:
                counts = await asyncio.to_thread(_brain_mod().scan)
                return JSONResponse({"ok": True, "counts": counts})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.get("/api/brain/graph")
        async def brain_graph(request: Request):
            if not _local(request):
                return JSONResponse({"error": "local only"}, status_code=403)
            try:
                return JSONResponse(_brain_mod().graph())
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.get("/api/brain/node")
        async def brain_node(request: Request, id: int = 0):
            if not _local(request):
                return JSONResponse({"error": "local only"}, status_code=403)
            n = _brain_mod().node(id)
            return JSONResponse(n or {"error": "not found"})

        @app.get("/api/brain/stats")
        async def brain_stats(request: Request):
            if not _local(request):
                return JSONResponse({"error": "local only"}, status_code=403)
            return JSONResponse(_brain_mod().stats())

        @app.get("/api/brain/search")
        async def brain_search(request: Request, q: str = ""):
            if not _local(request):
                return JSONResponse({"error": "local only"}, status_code=403)
            return JSONResponse({"results": _brain_mod().search(q, 12) if q else []})

        @app.get("/tv", response_class=HTMLResponse)
        async def tv_page(request: Request):
            # 10-foot HUD for a Fire TV. Trusted devices (this machine / the user's Tailscale)
            # get a full token so they can also talk to and control Rencora from the TV;
            # any other reachable device gets a read-only display token (feed only).
            tok = secrets.token_urlsafe(24)
            self._tokens.add(tok)
            if not _local(request):
                self._display_tokens.add(tok)          # untrusted LAN viewer = display only
            html = self._tv_html.replace("__TVTOKEN__", tok)
            return HTMLResponse(html)

        @app.get("/api/setup-status")
        async def setup_status():
            cfgp = BASE_DIR / "config" / "api_keys.json"
            ownerp = BASE_DIR / "config" / "owner.json"
            has_key, name = False, ""
            try:
                has_key = bool(json.loads(cfgp.read_text(encoding="utf-8")).get("gemini_api_key"))
            except Exception:
                pass
            try:
                name = json.loads(ownerp.read_text(encoding="utf-8")).get("name", "")
            except Exception:
                pass
            return JSONResponse({"has_key": has_key, "name": name})

        @app.post("/api/setup")
        async def setup_save(request: Request):
            if not _local(request):
                return JSONResponse({"ok": False, "error": "Nur auf deinen Geräten möglich."}, status_code=403)
            try:
                body = await request.json()
            except Exception:
                return JSONResponse({"ok": False, "error": "Ungültige Daten."}, status_code=400)
            cfgp = BASE_DIR / "config" / "api_keys.json"
            ownerp = BASE_DIR / "config" / "owner.json"
            key = (body.get("gemini_api_key") or "").strip()
            name = (body.get("name") or "").strip()
            try:
                if key:
                    try:
                        cfg = json.loads(cfgp.read_text(encoding="utf-8"))
                    except Exception:
                        cfg = {}
                    cfg["gemini_api_key"] = key
                    cfg.setdefault("os_system", "windows")
                    cfgp.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
                if name:
                    try:
                        own = json.loads(ownerp.read_text(encoding="utf-8"))
                    except Exception:
                        own = {}
                    own["name"] = name
                    own.setdefault("assistant_name", "Rencora")
                    ownerp.write_text(json.dumps(own, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
            return JSONResponse({"ok": True})

        @app.get("/local", response_class=HTMLResponse)
        async def local_login(request: Request, to: str = "/home"):
            # One-click auth for this machine or the user's own Tailscale devices
            # (their phone from anywhere counts; strangers do not). Removes the QR/PIN dance.
            if not _local(request):
                return HTMLResponse("Login only available on your own devices.",
                                    status_code=403)
            tok = secrets.token_urlsafe(32)
            self._tokens.add(tok)                       # plaintext commands only (no AES key)
            dest = to if to.startswith("/") and "//" not in to else "/home"
            return HTMLResponse(
                "<!DOCTYPE html><meta charset=utf-8><body style='background:#03040a'>"
                "<script>sessionStorage.setItem('jarvis_token','" + tok + "');"
                "location.replace('" + dest + "');</script></body>")

        @app.post("/login")
        async def login(req: Request):
            body    = await req.json()
            entered = str(body.get("pin", "")).strip().upper()
            now     = time.time()
            if entered in self._pending_keys and self._pending_keys[entered] > now:
                del self._pending_keys[entered]          # one-time use
                tok = secrets.token_urlsafe(32)
                self._tokens.add(tok)
                self._token_keys[tok] = entered
                self._aes_key(entered)                   # pre-derive & cache
                if self._connect_callback:
                    self._connect_callback()
                asyncio.create_task(self.broadcast(
                    {"type": "sys", "text": "Remote connection established."}
                ))
                # Bearer token in response body — no cookies needed (works on any browser/HTTP)
                return JSONResponse({"ok": True, "token": tok})
            return JSONResponse({"ok": False, "error": "Invalid or expired key"},
                                status_code=401)

        @app.get("/auto-login")
        async def auto_login(key: str = ""):
            """QR code target — validates one-time key, creates session, redirects phone."""
            now = time.time()
            if not key or key not in self._pending_keys or self._pending_keys[key] <= now:
                return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>
  body{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}
  h2{color:#f87171;margin-bottom:12px}p{color:#5e6a7e;font-size:14px}
</style></head>
<body><div><h2>Link Expired</h2>
<p>Press <strong style="color:#dde3ed">Remote Control</strong> in JARVIS to get a new QR code.</p>
</div></body></html>""")

            del self._pending_keys[key]
            tok     = secrets.token_urlsafe(32)
            dev_tok = secrets.token_urlsafe(32)
            self._tokens.add(tok)
            self._token_keys[tok] = key
            self._aes_key(key)
            self._device_sessions[dev_tok] = {"session_key": key}

            if self._connect_callback:
                self._connect_callback()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Remote connection established via QR code."}
            ))

            return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>
  body{{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}}
  p{{color:#5e6a7e;font-size:14px}}
</style></head>
<body>
<script>
  sessionStorage.setItem('jarvis_token','{tok}');
  sessionStorage.setItem('jarvis_key','{key}');
  localStorage.setItem('jarvis_device_token','{dev_tok}');
  setTimeout(function(){{location.replace('/')}},400);
</script>
<p>Connecting to JARVIS…</p>
</body></html>""")

        @app.post("/api/device-login")
        async def device_login_ep(req: Request):
            """Return a fresh auth token for a previously paired device token."""
            try:
                body = await req.json()
            except Exception:
                return JSONResponse({"ok": False}, status_code=400)
            dev_tok = (body.get("device_token") or "").strip()
            if not dev_tok or dev_tok not in self._device_sessions:
                return JSONResponse({"ok": False}, status_code=401)
            session_key = self._device_sessions[dev_tok]["session_key"]
            tok = secrets.token_urlsafe(32)
            self._tokens.add(tok)
            self._token_keys[tok] = session_key
            self._aes_key(session_key)
            if self._connect_callback:
                self._connect_callback()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Known device reconnected automatically."}
            ))
            return JSONResponse({"ok": True, "token": tok, "key": session_key})

        @app.post("/api/revoke-devices")
        async def revoke_devices(req: Request):
            """Invalidate all persistent device tokens (admin action)."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            count = len(self._device_sessions)
            self._device_sessions.clear()
            return JSONResponse({"ok": True, "revoked": count})

        @app.post("/api/command")
        async def command(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body  = await req.json()
            token = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            enc   = body.get("enc", "")
            if enc:
                text = self._decrypt(token, enc)
                if text is None:
                    return JSONResponse({"error": "Decryption failed"}, status_code=400)
            else:
                text = (body.get("text") or "").strip()
            if text:
                await self._command_queue.put(text)
                if self._wake_callback:
                    self._wake_callback()
            return JSONResponse({"ok": True})

        @app.post("/api/wake")
        async def wake_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            if self._wake_callback:
                self._wake_callback()
            return JSONResponse({"ok": True})

        @app.post("/api/listen-mode")
        async def listen_mode_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                body = await req.json()
            except Exception:
                body = {}
            on = bool(body.get("continuous"))
            if self._listen_mode_callback:
                self._listen_mode_callback(on)
            return JSONResponse({"ok": True, "continuous": on})

        # ── Phone mic real-time audio → Gemini Live ──────────────────────────

        @app.websocket("/ws/phone-audio")
        async def phone_audio_ws(websocket: WebSocket, token: str = ""):
            tok = token.strip()
            if not tok or tok not in self._tokens:
                await websocket.close(code=4001)
                return
            await websocket.accept()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Phone microphone live."}
            ))
            try:
                while True:
                    data = await websocket.receive_bytes()
                    try:
                        self._phone_audio_queue.put_nowait(
                            {"data": data, "mime_type": "audio/pcm"}
                        )
                    except asyncio.QueueFull:
                        pass  # drop frame rather than block
            except WebSocketDisconnect:
                pass
            finally:
                asyncio.create_task(self.broadcast(
                    {"type": "sys", "text": "Phone microphone stopped."}
                ))

        # ── File sharing ──────────────────────────────────────────────────────

        def _safe_filename(raw: str) -> str:
            name = Path(raw).name                          # strip path components
            name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(". ")
            return name or "upload"

        if _UPLOAD_OK:
            @app.post("/api/upload")
            async def upload_file(req: Request, file: UploadFile = FastAPIFile(...)):
                if not _auth(req):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                safe = _safe_filename(file.filename or "upload")
                dest = self._uploads_dir / safe
                stem, suffix = Path(safe).stem, Path(safe).suffix
                counter = 1
                while dest.exists():
                    dest = self._uploads_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                size = 0
                max_bytes = MAX_UPLOAD_MB * 1024 * 1024
                try:
                    with open(dest, "wb") as fout:
                        while True:
                            chunk = await file.read(65536)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > max_bytes:
                                fout.close()
                                dest.unlink(missing_ok=True)
                                return JSONResponse(
                                    {"error": f"File too large (max {MAX_UPLOAD_MB} MB)"},
                                    status_code=413,
                                )
                            fout.write(chunk)
                except Exception as exc:
                    try:
                        dest.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return JSONResponse({"error": str(exc)}, status_code=500)

                asyncio.create_task(self.broadcast({
                    "type": "file_received",
                    "name": dest.name,
                    "size": size,
                    "saved_to": str(self._uploads_dir),
                }))
                return JSONResponse({"ok": True, "name": dest.name, "size": size})
        else:
            @app.post("/api/upload")
            async def upload_unavailable(req: Request):
                return JSONResponse(
                    {"error": "File uploads require: pip install python-multipart"},
                    status_code=503,
                )

        @app.get("/api/files")
        async def list_files(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            files = []
            try:
                for f in sorted(
                    (p for p in self._uploads_dir.iterdir() if p.is_file()),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                ):
                    files.append({"name": f.name, "size": f.stat().st_size})
            except Exception:
                pass
            return JSONResponse({"files": files})

        @app.get("/uploads/{filename}")
        async def download_file(filename: str, token: str = ""):
            # Auth via query param — browser <a download> can't send custom headers
            tok = token.strip()
            if not tok or tok not in self._tokens:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            safe = re.sub(r'[/\\]', '', filename)
            path = self._uploads_dir / safe
            if not path.exists() or not path.is_file():
                return JSONResponse({"error": "Not found"}, status_code=404)
            return FileResponse(str(path), filename=safe)

        @app.websocket("/ws")
        async def ws_ep(websocket: WebSocket, token: str = ""):
            tok = token.strip()
            if not tok or tok not in self._tokens:
                await websocket.close(code=4001)
                return
            await websocket.accept()
            self._clients.add(websocket)
            for entry in self._history[-50:]:
                try:
                    await websocket.send_json(entry)
                except Exception:
                    break
            try:
                while True:
                    data = await websocket.receive_json()
                    if data.get("type") == "command" and tok not in self._display_tokens:
                        enc = data.get("enc", "")
                        t   = self._decrypt(tok, enc) if enc else (data.get("text") or "").strip()
                        if t:
                            await self._command_queue.put(t)
                            if self._wake_callback:
                                self._wake_callback()
            except WebSocketDisconnect:
                pass
            finally:
                self._clients.discard(websocket)

        return app

    # ── serve ─────────────────────────────────────────────────────────────

    async def _serve_alias(self) -> None:
        """Second HTTPS server on PORT+1 sharing the same app and in-memory state.
        Chrome HTTPS-upgrades any bare IP:PORT the user types, so this port also needs TLS.
        User types IP:8001 → Chrome tries https → self-signed cert warning → accept once → done."""
        ssl_key  = BASE_DIR / "config" / "certs" / "jarvis.key"
        ssl_cert = BASE_DIR / "config" / "certs" / "jarvis.crt"
        asyncio.get_event_loop().run_in_executor(None, _ensure_network_access, PORT + 1)
        cfg = uvicorn.Config(
            self.app, host="0.0.0.0", port=PORT + 1, log_level="warning",
            ssl_keyfile=str(ssl_key), ssl_certfile=str(ssl_cert),
        )
        print(f"[Dashboard] Manual entry:  {self._ip}:{PORT + 1}  (type in browser, accept cert once)")
        await uvicorn.Server(cfg).serve()

    async def serve(self) -> None:
        if not _DEPS_OK:
            print("[Dashboard] fastapi/uvicorn not installed — dashboard disabled.")
            print("[Dashboard] Run:  pip install fastapi 'uvicorn[standard]' cryptography")
            return

        # Firewall setup runs in a thread — uvicorn starts immediately,
        # no waiting for UAC dialogs or subprocess timeouts.
        asyncio.get_event_loop().run_in_executor(None, _ensure_network_access, PORT)

        # Generate the TLS pair on first run so no private key ships in the repo.
        _ensure_certs()

        use_ssl  = self._ssl_enabled()
        ssl_key  = BASE_DIR / "config" / "certs" / "jarvis.key"
        ssl_cert = BASE_DIR / "config" / "certs" / "jarvis.crt"

        if use_ssl:
            asyncio.create_task(self._serve_alias())

        cfg = uvicorn.Config(
            self.app, host="0.0.0.0", port=PORT, log_level="warning",
            **({"ssl_keyfile": str(ssl_key), "ssl_certfile": str(ssl_cert)} if use_ssl else {}),
        )

        proto = "https" if use_ssl else "http"
        print(f"[Dashboard] {proto}://{self._ip}:{PORT}")
        print("[Dashboard] Press 'Remote Control' in JARVIS UI to get the QR code.")
        await uvicorn.Server(cfg).serve()
