"""
Rencora Aufgaben — 'merk dir …', 'setz auf die Liste …', 'was steht auf meiner Liste', 'streich …'.
Schreibt in dieselbe Liste, die die Info-Wall (/wall) anzeigt (config/wall_tasks.json) — per
Sprache hinzugefügte Aufgaben erscheinen dort sofort.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import json
from pathlib import Path
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

_FILE = Path(__file__).resolve().parent.parent / "config" / "wall_tasks.json"

PLUGIN = {
    "name": "remember_task",
    "description": (
        "Aufgaben-/Merkliste, die auch auf der Info-Wall erscheint. Nutze es bei: "
        "'merk dir …', 'setz … auf die Liste', 'erinnere mich an …', 'was steht auf meiner Liste' (list), "
        "'streich … / hab … erledigt' (done), 'Liste leeren' (clear). actions: add | list | done | clear."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add | list | done | clear"},
            "text": {"type": "STRING", "description": "Aufgabentext (für add / done)"},
        },
        "required": ["action"],
    },
}


def _load():
    try:
        return json.loads(_FILE.read_text(encoding="utf-8")).get("tasks", [])
    except Exception:
        return []


def _save(tasks):
    try:
        _FILE.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "list").strip().lower()
    text = (parameters.get("text") or "").strip()
    tasks = _load()

    if action in ("add", "merken", "hinzufügen"):
        if not text:
            return "Was soll ich mir merken?"
        tasks.append({"text": text, "done": False})
        _save(tasks)
        return "Notiert: " + text + ". Steht jetzt auf deiner Liste."
    if action in ("done", "erledigt", "streich", "streichen"):
        if not text:
            return "Welche Aufgabe ist erledigt?"
        low = text.lower()
        hit = None
        for t in tasks:
            if low in t.get("text", "").lower():
                t["done"] = True
                hit = t["text"]
                break
        _save(tasks)
        return ("Erledigt: " + hit) if hit else ("Ich finde '" + text + "' nicht auf der Liste.")
    if action in ("clear", "leeren"):
        _save([])
        return "Liste geleert."
    # list
    open_ = [t["text"] for t in tasks if not t.get("done")]
    if not open_:
        return "Deine Liste ist leer."
    return "Auf deiner Liste: " + ", ".join(open_) + "."
