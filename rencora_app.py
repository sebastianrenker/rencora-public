"""
Rencora launcher — the one thing you double-click.

1. Starts the headless assistant (local plain-HTTP mode) if it isn't already running.
2. Opens the Rencora interface as a borderless app window (Chrome/Edge --app), already
   logged in via the localhost-only /local route (no QR/PIN needed).

Run it silently via "Rencora starten.vbs".
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import os
import sys
import socket
import subprocess
import time
import pathlib
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

# When frozen to an .exe, __file__ is a temp dir — use the exe's own folder instead
# (place Rencora.exe inside the Mark-LI folder).
if getattr(sys, "frozen", False):
    ROOT = pathlib.Path(sys.executable).resolve().parent
else:
    ROOT = pathlib.Path(__file__).resolve().parent


def _has_key():
    import json
    try:
        return bool(json.loads((ROOT / "config" / "api_keys.json").read_text(encoding="utf-8")).get("gemini_api_key"))
    except Exception:
        return False


URL = ("http://127.0.0.1:8000/setup" if not _has_key()
       else "http://127.0.0.1:8000/local?to=/home")


def _python():
    """Interpreter to launch run_headless.py with. When this launcher is itself a
    frozen .exe, sys.executable is the exe — find a real pythonw instead."""
    import shutil
    if getattr(sys, "frozen", False):
        for p in (
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\pythonw.exe"),
            shutil.which("pythonw"), shutil.which("python"),
            r"C:\Program Files\Python312\pythonw.exe",
        ):
            if p and os.path.exists(p):
                return p
        return "pythonw"
    return sys.executable


def _up():
    try:
        with socket.create_connection(("127.0.0.1", 8000), 0.4):
            return True
    except OSError:
        return False


def _find_browser():
    import shutil
    for c in ("chrome.exe", "chrome", "msedge.exe", "msedge"):
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


def main():
    # 1) ensure the backend is running
    if not _up():
        DETACHED = 0x00000008 | 0x00000200      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen([_python(), str(ROOT / "run_headless.py"), "--local"],
                             cwd=str(ROOT), creationflags=DETACHED, close_fds=True)
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
        for _ in range(90):                      # wait up to ~45s for Gemini/dashboard boot
            if _up():
                break
            time.sleep(0.5)

    # 2) open the interface as an app window
    browser = _find_browser()
    try:
        if browser:
            subprocess.Popen([browser, "--app=" + URL, "--start-fullscreen", "--new-window"])
            return
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)
    import webbrowser
    webbrowser.open(URL)


if __name__ == "__main__":
    main()
