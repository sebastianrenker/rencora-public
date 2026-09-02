"""
Rencora Objekt-Analyse (Sprache) — analysiert, was die Kamera gerade erkannt hat: Bauteile,
Technik, Alltagsgegenstände. Erkennung läuft kostenlos im Browser (Objekt-Labor / Tisch),
die Erklärung kommt von Grok/Groq — komplett ohne Gemini-Kontingent.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""

PLUGIN = {
    "name": "analyze_object",
    "description": (
        "Analysiert Objekte/Bauteile/Technik, die die Kamera erkannt hat (kostenlos, kein Gemini). "
        "Nutze es bei: 'was ist das', 'analysier das Bauteil', 'erklär mir dieses Objekt', "
        "'wie zerlege ich das' (mode=zerlegen), 'wie baue ich das zusammen' (mode=bauen), "
        "'analysiere das genau' (mode=analysieren). Braucht eine offene Kamera-Seite "
        "(Objekt-Labor, Tisch oder Leinwand)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "mode": {"type": "STRING", "description": "identify | analysieren | zerlegen | bauen"},
        },
        "required": [],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    try:
        from actions.lab import load_labels, analyze
    except Exception as e:
        return "Das Objekt-Labor ist nicht verfügbar: " + str(e)
    labels = load_labels()
    if not labels:
        return ("Ich sehe gerade keine erkannten Objekte. Öffne das Objekt-Labor (oder Tisch/Leinwand "
                "mit Kamera) und halte das Bauteil davor.")
    mode = (parameters.get("mode") or "identify").strip()
    out = analyze(labels, mode)
    if not out:
        return "Ich konnte das gerade nicht analysieren."
    if player:
        try:
            player.write_log("JARVIS: " + out[:200])
        except Exception:
            pass
    return out
