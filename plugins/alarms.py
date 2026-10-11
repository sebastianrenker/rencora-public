"""
Rencora recurring alarms / routines — 'jeden Werktag 7 Uhr wecken', 'täglich 22 Uhr'.
Unlike the countdown timer, these repeat on chosen weekdays at a clock time. A background
checker (started on import; Rencora runs continuously) fires them: Rencora announces it
(via request_say) + an audible alarm.

Persisted to config/alarms.json. Engine: Mark-LI by FatihMakes (CC BY-NC 4.0).
"""
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

_FILE = Path(__file__).resolve().parent.parent / "config" / "alarms.json"
_SAY = {"fn": None}          # set from run() when a player with request_say is available

PLUGIN = {
    "name": "alarm",
    "description": (
        "Recurring alarms and wake-up routines that repeat on weekdays at a clock time "
        "(unlike the countdown 'timer'). Use for 'weck mich jeden Werktag um 7', "
        "'täglich 22 Uhr erinnern', 'jeden Montag 9 Uhr'. "
        "actions: 'add' (needs time 'HH:MM'; optional days = list like ['Mo','Di'] or 'werktags'/'täglich'; "
        "optional label), 'list', 'remove' (needs label or time)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add | list | remove"},
            "time": {"type": "STRING", "description": "Clock time HH:MM (24h)"},
            "days": {"type": "STRING", "description": "'täglich', 'werktags', 'wochenende', or e.g. 'Mo,Di,Fr'"},
            "label": {"type": "STRING", "description": "Optional name, e.g. 'Aufstehen'"},
        },
        "required": ["action"],
    },
}

_DAYMAP = {"mo": 0, "di": 1, "mi": 2, "do": 3, "fr": 4, "sa": 5, "so": 6}


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
        _swallow_log.debug("ignored error", exc_info=True)
    return None


_FFPLAY = _find_ffplay()


def _beep():
    if not _FFPLAY:
        return
    for _ in range(4):
        try:
            subprocess.run([_FFPLAY, "-f", "lavfi", "-i", "sine=frequency=880:duration=0.4",
                            "-nodisp", "-autoexit", "-loglevel", "quiet"],
                           creationflags=0x08000000, timeout=3)
        except Exception:
            break
        time.sleep(0.15)


def _load():
    try:
        return json.loads(_FILE.read_text(encoding="utf-8")).get("alarms", [])
    except Exception:
        return []


def _save(alarms):
    _FILE.write_text(json.dumps({"alarms": alarms}, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_days(days):
    d = (days or "täglich").strip().lower()
    if d in ("täglich", "taeglich", "jeden tag", "daily"):
        return [0, 1, 2, 3, 4, 5, 6]
    if d in ("werktags", "wochentags", "weekdays"):
        return [0, 1, 2, 3, 4]
    if d in ("wochenende", "weekend"):
        return [5, 6]
    out = []
    for tok in d.replace(";", ",").replace(" ", ",").split(","):
        out.append(_DAYMAP.get(tok[:2], None))
    return [x for x in out if x is not None] or [0, 1, 2, 3, 4, 5, 6]


def _checker():
    last_fired = ""
    while True:
        try:
            now = time.localtime()
            hm = time.strftime("%H:%M", now)
            wd = now.tm_wday
            stamp = time.strftime("%Y%m%d%H%M", now)
            if stamp != last_fired:
                for a in _load():
                    if a.get("time") == hm and wd in a.get("days", []):
                        last_fired = stamp
                        label = a.get("label", "Wecker")
                        say = _SAY["fn"]
                        if say:
                            try:
                                say("Sag dem Nutzer freundlich, dass sein Wecker '" + label + "' jetzt klingelt.")
                            except Exception:
                                _swallow_log.debug("ignored error", exc_info=True)
                        _beep()
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
        time.sleep(20)


threading.Thread(target=_checker, daemon=True).start()


def run(parameters: dict, player=None, session_memory=None) -> str:
    if player is not None:
        _SAY["fn"] = getattr(player, "request_say", None)
    action = (parameters.get("action") or "list").strip().lower()
    try:
        alarms = _load()
        if action == "add":
            t = (parameters.get("time") or "").strip()
            if not t or ":" not in t:
                return "Um welche Uhrzeit (HH:MM) soll ich wecken?"
            days = _parse_days(parameters.get("days"))
            label = (parameters.get("label") or "Wecker").strip()
            alarms.append({"time": t, "days": days, "label": label})
            _save(alarms)
            names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            out = ("Wecker '" + label + "' auf " + t + " gestellt (" +
                   ", ".join(names[d] for d in days) + ").")
        elif action == "remove":
            q = (parameters.get("label") or parameters.get("time") or "").strip().lower()
            before = len(alarms)
            alarms = [a for a in alarms if q not in a.get("label", "").lower() and q != a.get("time", "")]
            _save(alarms)
            out = str(before - len(alarms)) + " Wecker entfernt."
        else:
            names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            out = ("Keine Wecker gestellt." if not alarms
                   else "Deine Wecker: " + " | ".join(
                       a["label"] + " " + a["time"] + " (" + ",".join(names[d] for d in a.get("days", [])) + ")"
                       for a in alarms))
    except Exception as e:
        return "Die Wecker-Verwaltung ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return out
