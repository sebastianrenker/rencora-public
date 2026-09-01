"""
Rencora interests — the owner's topics for daily updates/briefings.
'merk dir dass mich X interessiert', 'gib mir mein Update' (Rencora reads these and
briefs on each using the right tools: news, weather, github, etc.).

Persisted to config/interests.json.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
from pathlib import Path

_FILE = Path(__file__).resolve().parent.parent / "config" / "interests.json"

PLUGIN = {
    "name": "interests",
    "description": (
        "Store and read the owner's topics of interest for updates/briefings. "
        "actions: 'add' (needs topic, e.g. 'KI-News', 'Wetter Berlin', 'meine GitHub-Aktivität', "
        "'Bitcoin-Kurs'), 'remove' (needs topic), 'show' (list them). "
        "When the owner asks for 'mein Update' / 'Tagesupdate' / 'brief mich', call this with "
        "action='show', then briefly cover EACH topic using the appropriate tools (web_search "
        "news, weather, github_info, etc.)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add | remove | show"},
            "topic": {"type": "STRING", "description": "The topic (for add/remove)"},
        },
        "required": ["action"],
    },
}


def _load():
    try:
        d = json.loads(_FILE.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else d.get("topics", [])
    except Exception:
        return []


def _save(topics):
    _FILE.write_text(json.dumps({"topics": topics}, ensure_ascii=False, indent=2), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "show").strip().lower()
    topic = (parameters.get("topic") or "").strip()
    try:
        topics = _load()
        if action == "add":
            if not topic:
                out = "Welches Thema soll ich mir merken?"
            elif topic.lower() in [t.lower() for t in topics]:
                out = topic + " ist schon in deinen Interessen."
            else:
                topics.append(topic); _save(topics)
                out = "Gemerkt: " + topic + ". Du hast jetzt " + str(len(topics)) + " Themen fürs Update."
        elif action == "remove":
            m = next((t for t in topics if t.lower() == topic.lower()), None)
            if m:
                topics.remove(m); _save(topics)
                out = topic + " aus deinen Interessen entfernt."
            else:
                out = topic + " war nicht in deinen Interessen."
        else:
            out = ("Du hast noch keine Interessen gespeichert. Sag z.B. 'merk dir KI-News'."
                   if not topics else "Deine Update-Themen: " + ", ".join(topics) + ".")
    except Exception as e:
        return "Die Interessen-Verwaltung ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            pass
    return out
