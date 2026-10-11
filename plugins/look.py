"""
Rencora Live-Kamera-Vision — 'Rencora, was siehst du?'. Beschreibt, was die Kamera (Tisch-/
Holo-Seite) gerade sieht. Nutzt den zuletzt von einer Kamera-Seite gepushten Frame
(actions.vision.FRAME_PATH) und Gemini-Vision. So sieht Rencora die Umgebung, ohne mit dem
Browser um die Webcam zu kämpfen.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

PLUGIN = {
    "name": "look",
    "description": (
        "Beschreibt, was die Kamera gerade sieht (Live-Kamera-Vision). Nutze es bei: "
        "'was siehst du', 'schau mal', 'was ist das', 'was liegt vor dir', 'beschreib die Umgebung', "
        "'lies das vor der Kamera'. Optional eine konkrete Frage zum Bild mitgeben. "
        "Braucht eine offene Kamera-Seite (Tisch/3D), die den Frame liefert."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "question": {"type": "STRING", "description": "Optionale konkrete Frage zum Kamerabild"},
        },
        "required": [],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    try:
        from actions.vision import describe_latest, latest_frame_age
    except Exception as e:
        return "Die Kamera-Vision ist nicht verfügbar: " + str(e)
    age = latest_frame_age()
    if age < 0:
        return ("Ich habe gerade kein Kamerabild. Öffne die Tisch- oder 3D-Seite (Kamera aktiv), "
                "dann sehe ich, was davor liegt.")
    if age > 120:
        return ("Mein letztes Kamerabild ist über zwei Minuten alt. Lass bitte die Tisch-/3D-Seite "
                "mit aktiver Kamera offen, dann schaue ich erneut.")
    q = (parameters.get("question") or "").strip()
    try:
        out = describe_latest(q)
    except Exception as e:
        return "Die Kamera-Analyse ist fehlgeschlagen: " + str(e)
    out = (out or "").strip() or "Ich konnte nichts Eindeutiges erkennen."
    if player:
        try:
            player.write_log("JARVIS: " + out[:200])
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return out
