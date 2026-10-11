"""
Rencora Nachrichten-Überblick — holt die aktuellen Schlagzeilen aus deinen konfigurierten
Feeds (config/wall.json) und lässt Grok/Groq daraus einen kurzen, gesprochenen Überblick machen. Nutzt
den schnellen Zweitanbieter (spart Gemini-Tokens); ohne Grok fällt es auf die reinen
Schlagzeilen zurück.

'fass die Nachrichten zusammen', 'Tagesüberblick', 'was gibt's Neues', 'Nachrichtenüberblick'.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

PLUGIN = {
    "name": "news_briefing",
    "description": (
        "Gesprochener Nachrichten-Überblick aus den aktuellen Schlagzeilen deiner Feeds. "
        "Nutze es bei: 'fass die Nachrichten zusammen', 'Tagesüberblick', 'was gibt es Neues', "
        "'Nachrichtenüberblick', 'lies mir die Lage zusammen'. Fasst per Grok/Groq zusammen (spart "
        "Gemini-Tokens); du sprichst das Ergebnis dann aus."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "focus": {"type": "STRING", "description": "Optionaler Schwerpunkt, z.B. 'nur regional' oder 'nur überregional'"},
        },
        "required": [],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    try:
        from actions.wall_data import news
    except Exception as e:
        return "Die Nachrichtenquellen sind nicht verfügbar: " + str(e)
    try:
        items = news(10)
    except Exception:
        items = []
    if not items:
        return "Ich konnte gerade keine Nachrichten laden."

    focus = (parameters.get("focus") or "").strip().lower()
    if "osthessen" in focus:
        items = [i for i in items if (i.get("source", "").lower().startswith("osthessen"))] or items
    elif "überregional" in focus or "ueberregional" in focus or "deutschland" in focus:
        items = [i for i in items if not i.get("source", "").lower().startswith("osthessen")] or items

    lines = []
    for it in items[:10]:
        src = it.get("source", "")
        place = (" [" + it["place"] + "]") if it.get("place") else ""
        lines.append(f"- ({src}{place}) {it.get('title', '')}")
    headlines = "\n".join(lines)

    # Grok/Groq fasst zusammen (schnell, spart Gemini); Fallback = rohe Schlagzeilen.
    try:
        from plugins.grok import grok_complete, is_configured
        if is_configured():
            prompt = ("Fasse die folgenden aktuellen Schlagzeilen zu einem knappen, gesprochenen "
                      "Nachrichtenüberblick auf Deutsch zusammen: 4 bis 6 flüssige Sätze, zuerst das "
                      "Regionale/Lokale, dann das Überregionale. Keine Aufzählung, kein "
                      "Vorwort, nur der Überblick.\n\nSCHLAGZEILEN:\n" + headlines)
            summary = grok_complete(prompt, "Du bist Rencora und gibst einen knappen Nachrichtenüberblick.")
            if summary:
                out = summary.strip()
                if player:
                    try:
                        player.write_log("JARVIS: " + out[:200])
                    except Exception:
                        _swallow_log.debug("ignored error", exc_info=True)
                return out
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)

    # Fallback ohne Grok: die wichtigsten Schlagzeilen vorlesen
    top = items[:5]
    spoken = "Die wichtigsten Meldungen: " + " | ".join(t.get("title", "") for t in top)
    return spoken
