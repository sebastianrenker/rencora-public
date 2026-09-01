"""
Rencora Unwetter-Warner — prüft im Hintergrund das Wetter für deinen Ort (config/wall.json)
und warnt proaktiv bei Gewitter, schwerem Regen/Schnee oder Sturm. Standardmäßig AN.
'Unwetter-Warnung aus/an', 'ist Unwetter angesagt' (check).
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import threading
import time

_SAY = {"fn": None, "log": None}
_STATE = {"on": True, "last_warn": 0.0, "started": False}

# WMO-Codes, die eine Warnung wert sind
_SEVERE = {65: "starker Regen", 75: "starker Schneefall", 82: "heftige Schauer",
           95: "Gewitter", 96: "Gewitter mit Hagel", 99: "schweres Gewitter mit Hagel"}
_WIND_KMH = 60.0

PLUGIN = {
    "name": "weather_alert",
    "description": (
        "Proaktive Unwetter-Warnung für deinen Ort (Gewitter, Sturm, schwerer Regen/Schnee). "
        "Läuft automatisch im Hintergrund. Nutze das Tool bei: 'ist Unwetter angesagt' (check), "
        "'Unwetter-Warnung aus' (off), 'Unwetter-Warnung an' (on). actions: check | on | off."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {"action": {"type": "STRING", "description": "check | on | off"}},
        "required": [],
    },
}


def prime(player):
    _SAY["fn"] = getattr(player, "request_say", None)
    _SAY["log"] = getattr(player, "write_log", None)


def _assess():
    """-> (severe_text | None, wetter-dict)."""
    try:
        from actions.wall_data import weather
        w = weather()
    except Exception:
        return (None, None)
    code = w.get("code")
    wind = w.get("wind") or 0
    reasons = []
    if code in _SEVERE:
        reasons.append(_SEVERE[code])
    if wind >= _WIND_KMH:
        reasons.append(f"Sturm ({round(wind)} km/h Wind)")
    return ((" und ".join(reasons) if reasons else None), w)


def _watch():
    time.sleep(20)
    while True:
        try:
            if _STATE["on"]:
                sev, w = _assess()
                now = time.time()
                if sev and (now - _STATE["last_warn"] > 3 * 3600):   # höchstens alle 3 h
                    _STATE["last_warn"] = now
                    city = (w or {}).get("city", "deinem Ort")
                    say = _SAY.get("fn")
                    if _SAY.get("log"):
                        try: _SAY["log"](f"JARVIS: Unwetter-Warnung {city}: {sev}")
                        except Exception: pass
                    if say:
                        try:
                            say(f"Warne den Nutzer ruhig und deutlich vor Unwetter in {city}: {sev}. "
                                f"Rate, sich darauf einzustellen.")
                        except Exception: pass
        except Exception:
            pass
        time.sleep(1800)   # alle 30 Minuten


def _ensure_daemon():
    if not _STATE["started"]:
        _STATE["started"] = True
        threading.Thread(target=_watch, daemon=True).start()


_ensure_daemon()


def run(parameters: dict, player=None, session_memory=None) -> str:
    if player is not None:
        prime(player)
    _ensure_daemon()
    action = (parameters.get("action") or "check").strip().lower()
    if action in ("off", "aus"):
        _STATE["on"] = False
        return "Unwetter-Warnung ist aus."
    if action in ("on", "an"):
        _STATE["on"] = True
        return "Unwetter-Warnung ist an — ich melde mich bei Gewitter oder Sturm."
    # check
    sev, w = _assess()
    if not w:
        return "Ich kann das Wetter gerade nicht abrufen."
    city = w.get("city", "deinem Ort")
    if sev:
        return f"Achtung: Für {city} ist {sev} angesagt."
    return f"Für {city} ist aktuell kein Unwetter angesagt ({w.get('label', '')}, {round(w.get('wind') or 0)} km/h Wind)."
