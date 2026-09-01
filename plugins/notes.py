"""
Rencora notes/journal — quick searchable notes the owner dictates ("merk dir …",
"notier …", "schreib auf …"). Separate from the automatic memory. Persisted to
config/notes.json so they survive restarts.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
import time
from pathlib import Path

_FILE = Path(__file__).resolve().parent.parent / "config" / "notes.json"

PLUGIN = {
    "name": "notes",
    "description": (
        "Save, read, search and delete the owner's personal notes / journal. Use when they say "
        "'notier …', 'schreib auf …', 'merk dir als Notiz …', 'was hab ich notiert', "
        "'lies meine Notizen', 'such in Notizen nach X', 'lösche Notiz'. "
        "actions: 'add' (needs text), 'list', 'search' (needs query), 'delete' (needs query or index)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add | list | search | delete"},
            "text": {"type": "STRING", "description": "The note text (for add)"},
            "query": {"type": "STRING", "description": "Search/delete term"},
        },
        "required": ["action"],
    },
}


def _load():
    try:
        d = json.loads(_FILE.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else d.get("notes", [])
    except Exception:
        return []


def _save(notes):
    _FILE.write_text(json.dumps({"notes": notes}, ensure_ascii=False, indent=2), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "list").strip().lower()
    try:
        notes = _load()
        if action == "add":
            t = (parameters.get("text") or "").strip()
            if not t:
                return "Was soll ich notieren?"
            notes.append({"text": t, "ts": time.strftime("%d.%m.%Y %H:%M")})
            _save(notes)
            out = "Notiert. Du hast jetzt " + str(len(notes)) + " Notizen."
        elif action == "search":
            q = (parameters.get("query") or "").strip().lower()
            hits = [n for n in notes if q in n["text"].lower()]
            out = ("Keine Notiz zu '" + q + "' gefunden." if not hits
                   else "Gefunden: " + " | ".join(n["text"] for n in hits[:6]))
        elif action == "delete":
            q = (parameters.get("query") or "").strip().lower()
            before = len(notes)
            notes = [n for n in notes if q not in n["text"].lower()] if q else notes
            _save(notes)
            out = str(before - len(notes)) + " Notiz(en) gelöscht."
        else:
            out = ("Du hast noch keine Notizen." if not notes
                   else "Deine Notizen: " + " | ".join((n["ts"] + ": " + n["text"]) for n in notes[-8:]))
    except Exception as e:
        return "Die Notiz-Verwaltung ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out[:300])
        except Exception:
            pass
    return out
