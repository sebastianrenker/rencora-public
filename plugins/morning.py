"""
Rencora Morgenbriefing — Wetter + heutige Termine/Wecker + Nachrichten-Überblick in einem.
Rencora gibt es beim ersten Gruß am Morgen (siehe core/prompt.txt) oder auf Wunsch:
'Morgenbriefing', 'guten Morgen', 'brief mich', 'was steht heute an'.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import json
import time
from pathlib import Path

_ALARMS = Path(__file__).resolve().parent.parent / "config" / "alarms.json"

PLUGIN = {
    "name": "morning_briefing",
    "description": (
        "Kompaktes Morgenbriefing: aktuelles Wetter + heutige Wecker/Termine + kurzer "
        "Nachrichten-Überblick, in einem gesprochenen Text. Nutze es beim ersten 'Guten Morgen'/"
        "'Hallo' am Morgen und bei: 'Morgenbriefing', 'brief mich', 'was steht heute an'."
    ),
    "parameters": {"type": "OBJECT", "properties": {}, "required": []},
}

_DAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _today_alarms():
    try:
        data = json.loads(_ALARMS.read_text(encoding="utf-8")).get("alarms", [])
    except Exception:
        return []
    wd = time.localtime().tm_wday
    out = []
    for a in data:
        if wd in a.get("days", []):
            out.append(a.get("label", "Wecker") + " um " + a.get("time", ""))
    return out


def run(parameters: dict, player=None, session_memory=None) -> str:
    parts = []

    # Wetter
    try:
        from actions.wall_data import weather
        w = weather()
        days = w.get("days") or []
        hi = days[0].get("max") if days else None
        parts.append(f"Wetter in {w.get('city','')}: {w.get('label','')}, aktuell {round(w.get('temp') or 0)} Grad"
                     + (f", heute bis {round(hi)} Grad" if hi is not None else "") + ".")
    except Exception:
        pass

    # Termine / Wecker heute
    al = _today_alarms()
    if al:
        parts.append("Heute anstehend: " + ", ".join(al) + ".")
    else:
        parts.append("Für heute sind keine Wecker oder Termine eingetragen.")

    # Nachrichten-Überblick (nutzt Grok/Groq)
    try:
        from plugins import briefing
        news = briefing.run({})
        if news and "konnte" not in news.lower()[:30]:
            parts.append("Kurz die Nachrichten: " + news)
    except Exception:
        pass

    out = " ".join(parts) if parts else "Ich konnte gerade kein Briefing erstellen."
    if player:
        try:
            player.write_log("JARVIS: Morgenbriefing")
        except Exception:
            pass
    return out
