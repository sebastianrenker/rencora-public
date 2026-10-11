"""
Rencora — headless background runner.

Runs the JARVIS/Mark-LI assistant loop WITHOUT the desktop GUI:
  - voice assistant (Gemini Live) running in the background
  - dashboard web server on :8000  ->  serves the Rencora holo interface at /holo

The assistant's own `run()` already starts the dashboard and the Gemini Live loop;
it only needs a `ui` object. We give it a no-op stub so no window is ever created.

Usage:
    pythonw run_headless.py           # silent background (no console window)
    python  run_headless.py           # background with console log
    python  run_headless.py --selftest  # build everything but DON'T connect to Gemini

Upstream engine: Mark 51 / Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import sys, os, asyncio, pathlib
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

ROOT = pathlib.Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# Under pythonw.exe there is NO console: sys.stdout / sys.stderr are None, so every
# print() in the assistant would raise and silently kill its asyncio tasks (incl. the
# dashboard server). Redirect all output to a log file so background mode runs cleanly.
if sys.stdout is None or sys.stderr is None:
    _logf = open(ROOT / "rencora_background.log", "a", buffering=1, encoding="utf-8", errors="replace")
    sys.stdout = _logf
    sys.stderr = _logf


class _Win:
    """Stand-in for the GUI's internal window handle."""
    _ready = True


class HeadlessUI:
    """No-op replacement for JarvisUI. Implements exactly the surface that
    JarvisLive touches on `self.ui` (see main.py), so nothing else changes."""

    def __init__(self):
        self.muted = False            # never auto-muted in background mode
        self.current_file = None
        self._win = _Win()

    # --- methods JarvisLive calls on the UI (all safe no-ops / logging) ---
    def write_log(self, msg=""):        print(f"[Rencora] {msg}", flush=True)
    def set_state(self, state=""):      pass
    def show_content(self, *a, **k):    pass
    def start_camera_stream(self, *a, **k): pass
    def stop_camera_stream(self, *a, **k):  pass
    def notify_phone_connected(self, *a, **k): pass
    def prompt_reconfig(self, *a, **k):
        print("[Rencora] Gemini API key invalid — fix config/api_keys.json", flush=True)
    def wait_for_api_key(self, *a, **k): pass

    # any other UI method the assistant might call -> harmless no-op
    def __getattr__(self, name):
        return lambda *a, **k: None


def _check_key():
    import json
    p = ROOT / "config" / "api_keys.json"
    try:
        key = json.load(open(p, encoding="utf-8")).get("gemini_api_key", "")
    except Exception as e:
        print(f"[Rencora] Cannot read {p}: {e}", flush=True); return False
    if not key:
        print("[Rencora] No gemini_api_key in config/api_keys.json — run the GUI once to set it.", flush=True)
        return False
    return True


def _find_chrome():
    import shutil
    for c in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        p = shutil.which(c)
        if p:
            return p
    for p in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ):
        if os.path.exists(p):
            return p
    return None


def _open_browser_when_ready(url):
    """Wait until the dashboard is listening, then open it as an app window."""
    import socket, time, webbrowser, subprocess
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", 8000), 0.4):
                break
        except OSError:
            time.sleep(0.5)
    chrome = _find_chrome()
    try:
        if chrome:
            subprocess.Popen([chrome, "--app=" + url, "--start-fullscreen", "--new-window"])
            return
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)
    try:
        webbrowser.open(url)
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)


def _run_dashboard_only():
    """No Gemini key yet: serve just the dashboard so /setup is reachable."""
    import uvicorn
    from dashboard.server import DashboardServer
    srv = DashboardServer()
    print("[Rencora] Kein Gemini-Key — Setup unter http://127.0.0.1:8000/setup", flush=True)
    uvicorn.run(srv.app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    if "--local" in sys.argv:
        os.environ["RENCORA_NO_SSL"] = "1"      # plain HTTP on localhost (no cert warning)

    has_key = _check_key()
    open_url = ("http://127.0.0.1:8000/setup" if not has_key
                else "http://127.0.0.1:8000/local?to=/home")
    if "--open" in sys.argv:
        import threading
        threading.Thread(target=_open_browser_when_ready, args=(open_url,), daemon=True).start()

    if not has_key:
        if "--selftest" in sys.argv:
            print("[Rencora] SELFTEST: no key — would serve /setup.", flush=True)
            return
        _run_dashboard_only()
        return

    import main as jarvis_main
    ui = HeadlessUI()
    jarvis = jarvis_main.JarvisLive(ui)

    if "--selftest" in sys.argv:
        print("[Rencora] SELFTEST: HeadlessUI + JarvisLive constructed OK (no Gemini connection).", flush=True)
        return

    try:                                    # keep the Brain index fresh in the background
        import brain_db
        brain_db.start_auto()
        print("[Rencora] Brain auto-scan started (incremental ~10min, GitHub ~hourly).", flush=True)
    except Exception as e:
        print("[Rencora] Brain auto-scan not started: " + str(e), flush=True)

    print("[Rencora] Background assistant starting… (http://127.0.0.1:8000/home)", flush=True)
    try:
        asyncio.run(jarvis.run())
    except KeyboardInterrupt:
        print("[Rencora] Shutting down.", flush=True)


if __name__ == "__main__":
    main()
