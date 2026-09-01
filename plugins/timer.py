"""
Rencora timers & alarms (Alexa-style) — 'set a timer for 10 minutes'.

In-process countdown timers. On expiry an audible alarm plays in the background
(ffplay sine beeps, no window). For fixed clock times / dates, the reminder tool is used.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import os
import shutil
import subprocess
import threading
import time

PLUGIN = {
    "name": "timer",
    "description": (
        "Countdown timers and alarms (like Alexa): 'stell einen Timer auf 10 Minuten', "
        "'Wecker in 90 Sekunden', 'Eieruhr 5 Minuten'. "
        "actions: 'set' (needs minutes and/or seconds, optional label), 'list', 'cancel' "
        "(optional label; without label cancels all). For a specific clock time or date use the reminder tool instead."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "set | list | cancel"},
            "minutes": {"type": "INTEGER", "description": "Minutes (for set)"},
            "seconds": {"type": "INTEGER", "description": "Seconds (for set)"},
            "label": {"type": "STRING", "description": "Optional name, e.g. 'Pizza', 'Pause'"},
        },
        "required": ["action"],
    },
}


def _find_ffplay():
    p = shutil.which("ffplay")
    if p:
        return p
    base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    try:
        for root, _d, files in os.walk(base):
            if "ffplay.exe" in files:
                return os.path.join(root, "ffplay.exe")
    except Exception:
        pass
    return None


_FFPLAY = _find_ffplay()


def _alarm():
    if not _FFPLAY:
        return
    for _ in range(4):
        try:
            subprocess.run([_FFPLAY, "-f", "lavfi", "-i", "sine=frequency=880:duration=0.45",
                            "-nodisp", "-autoexit", "-loglevel", "quiet"],
                           creationflags=0x08000000, timeout=3)
        except Exception:
            break
        time.sleep(0.15)


class TimerManager:
    def __init__(self):
        self.timers = {}
        self.lock = threading.Lock()
        self.counter = 0

    def set(self, total_seconds, label, say=None):
        self.counter += 1
        tid = self.counter
        label = label or ("Timer " + str(tid))
        def fire():
            with self.lock:
                self.timers.pop(tid, None)
            if say:                                        # let Rencora announce it
                try:
                    say("Sag dem Nutzer freundlich und kurz, dass der Timer '" + label + "' jetzt abgelaufen ist.")
                except Exception:
                    pass
            _alarm()
        t = threading.Timer(total_seconds, fire)
        t.daemon = True
        with self.lock:
            self.timers[tid] = {"label": label, "timer": t, "end": time.time() + total_seconds}
        t.start()
        return label

    def list(self):
        with self.lock:
            items = list(self.timers.values())
        if not items:
            return "Es laufen gerade keine Timer."
        parts = []
        for it in items:
            rem = max(0, int(it["end"] - time.time()))
            parts.append(it["label"] + " (" + str(rem // 60) + " Min " + str(rem % 60) + " Sek)")
        return "Aktive Timer: " + ", ".join(parts) + "."

    def cancel(self, label):
        with self.lock:
            ids = list(self.timers.keys())
            killed = 0
            for tid in ids:
                it = self.timers[tid]
                if (not label) or (label.lower() in it["label"].lower()):
                    it["timer"].cancel()
                    del self.timers[tid]
                    killed += 1
        if killed == 0:
            return "Ich habe keinen passenden Timer gefunden."
        return ("Alle " + str(killed) + " Timer abgebrochen." if not label
                else str(killed) + " Timer abgebrochen.")


_MGR = None
def _mgr():
    global _MGR
    if _MGR is None:
        _MGR = TimerManager()
    return _MGR


def _fmt(total):
    m, s = total // 60, total % 60
    if m and s:
        return str(m) + " Minuten " + str(s) + " Sekunden"
    if m:
        return str(m) + " Minuten"
    return str(s) + " Sekunden"


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "").strip().lower()
    m = _mgr()
    try:
        if action == "set":
            total = int(parameters.get("minutes") or 0) * 60 + int(parameters.get("seconds") or 0)
            if total <= 0:
                out = "Für wie lange soll ich den Timer stellen?"
            else:
                say = getattr(player, "request_say", None) if player else None
                label = m.set(total, (parameters.get("label") or "").strip(), say=say)
                out = "Timer " + label + " auf " + _fmt(total) + " gestellt."
        elif action == "list":
            out = m.list()
        elif action == "cancel":
            out = m.cancel((parameters.get("label") or "").strip())
        else:
            out = "Unbekannte Timer-Aktion. Möglich: set, list, cancel."
    except Exception as e:
        return "Die Timer-Steuerung ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            pass
    return out
