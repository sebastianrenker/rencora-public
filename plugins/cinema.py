"""
Rencora Kinomodus — eine Szene: Licht dimmen + Film auf die Leinwand/Fire-TV + leiser Hintergrund.
'Film ab', 'Kinomodus', 'mach Kinomodus an mit <Film>'. 'Kinomodus aus' beendet (Licht an, Video stopp).
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

PLUGIN = {
    "name": "cinema_mode",
    "description": (
        "Kinomodus als Szene: dimmt das Licht, spielt einen Film/ein Video auf der Leinwand/Fire-TV "
        "und stellt die Hintergrundmusik leise. Nutze es bei: 'Film ab', 'Kinomodus', "
        "'mach Kinomodus an mit X', 'starte Filmabend'. 'off' beendet (Licht an, Video stopp). "
        "actions: on (optional query = Film), off."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "on | off"},
            "query": {"type": "STRING", "description": "Film/Video-Titel für action=on (optional)"},
        },
        "required": [],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "on").strip().lower()

    if action in ("off", "aus", "ende", "stop", "stopp"):
        try:
            from plugins import smarthome
            smarthome.run({"action": "on", "device": "Licht"})
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
        try:
            from plugins import music
            music._player().stop_video()
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
        return "Kinomodus beendet — Licht ist wieder an und das Video gestoppt."

    steps = []
    # 1) Licht dimmen (Szene 'Kino', sonst auf niedrigen Wert)
    try:
        from plugins import smarthome
        r = smarthome.run({"action": "scene", "device": "Kino"})
        if r and "nicht" in r.lower():
            smarthome.run({"action": "set", "device": "Licht", "value": 15})
        steps.append("Licht gedimmt")
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)
    # 2) Hintergrundmusik leise
    try:
        from plugins import music
        music._player().set_volume(20)
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)
    # 3) Film auf die Leinwand / Fire-TV
    query = (parameters.get("query") or "").strip()
    if query:
        try:
            from plugins import music
            music._player().play_video(query, player)
            steps.append("Film läuft: " + query)
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    else:
        steps.append("bereit für deinen Film — sag z.B. 'spiel <Titel> auf der Leinwand'")
    return "Kinomodus an — " + ", ".join(steps) + ". Sag 'Kinomodus aus' zum Beenden."
