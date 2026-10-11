"""
Rencora Globus — Sprachsteuerung für den 3D-Satellitenglobus (/globe). Rencora findet JEDEN
Ort (auch die kleinsten) über OpenStreetMap-Nominatim und lässt den Globus dorthin fliegen,
zoomen oder rotieren.

'zeig mir X auf dem Globus', 'zoom auf X', 'flieg nach X', 'dreh den Globus zu X',
'wo liegt X', 'dreh den Globus' (spin), 'zurück zur Weltansicht' (home).

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import json
import urllib.parse
import urllib.request
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

PLUGIN = {
    "name": "globe",
    "description": (
        "Steuert den 3D-Satellitenglobus (/globe): fliegt/zoomt/dreht zu JEDEM Ort der Erde — "
        "auch kleinste Dörfer, Straßen, Berge, Seen. Nutze es bei: 'zeig mir X auf dem Globus', "
        "'zoom auf X', 'flieg nach X', 'dreh den Globus zu X', 'wo liegt X', "
        "'dreh den Globus' (rotieren), 'zurück zur Weltansicht'. "
        "actions: 'fly' (needs place = Ortsname/Adresse), 'spin' (rotieren an/aus), 'home' (ganze Erde)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "fly | spin | home"},
            "place": {"type": "STRING", "description": "Ortsname / Adresse für action=fly"},
        },
        "required": [],
    },
}


def _geocode(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "Rencora-Globe/1.0 (personal use)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        if data:
            d = data[0]
            return (float(d["lat"]), float(d["lon"]), d.get("display_name", q))
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)
    return None


def run(parameters: dict, player=None, session_memory=None) -> str:
    fly = getattr(player, "globe_fly", None) if player else None
    if not fly:
        return "Der Globus ist gerade nicht erreichbar. Öffne die Globus-Seite."
    action = (parameters.get("action") or "").strip().lower()
    place = (parameters.get("place") or "").strip()

    if action == "spin":
        fly(0, 0, "__spin__")
        return "Ich lasse den Globus rotieren. Sag 'stopp', um ihn anzuhalten."
    if action == "home" or (not place and action in ("", "reset")):
        fly(0, 0, "__home__")
        return "Zurück zur Weltansicht."
    if not place:
        return "Welchen Ort soll ich auf dem Globus zeigen?"

    hit = _geocode(place)
    if not hit:
        return "Diesen Ort konnte ich nicht finden: " + place
    lat, lon, name = hit
    fly(lat, lon, name)
    short = name.split(",")[0]
    if player:
        try:
            player.write_log(f"JARVIS: Globus → {name} ({lat:.4f}, {lon:.4f})")
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return "Ich fliege auf dem Globus zu " + short + "."
