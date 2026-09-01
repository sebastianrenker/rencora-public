"""
Rencora lists (Alexa-style) — shopping list, to-do list, any named list.
Persisted to config/lists.json so items survive restarts.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
from pathlib import Path

_FILE = Path(__file__).resolve().parent.parent / "config" / "lists.json"

PLUGIN = {
    "name": "lists",
    "description": (
        "Manage named lists like a shopping list or to-do list (like Alexa): "
        "'setz Milch auf die Einkaufsliste', 'was steht auf meiner Einkaufsliste', "
        "'füge X zur To-do-Liste hinzu', 'streich Brot von der Liste', 'Liste leeren'. "
        "actions: 'add' (needs item, optional list_name), 'remove' (needs item), "
        "'show' (optional list_name), 'clear' (optional list_name), 'all' (show all lists). "
        "Default list_name is 'einkaufsliste'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add | remove | show | clear | all"},
            "item": {"type": "STRING", "description": "The item (for add/remove)"},
            "list_name": {"type": "STRING", "description": "List name, default 'einkaufsliste'"},
        },
        "required": ["action"],
    },
}


def _load():
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data):
    _FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "").strip().lower()
    name = (parameters.get("list_name") or "einkaufsliste").strip().lower()
    item = (parameters.get("item") or "").strip()
    try:
        data = _load()
        if action == "add":
            if not item:
                out = "Was soll ich auf die " + name + " setzen?"
            else:
                data.setdefault(name, [])
                if item.lower() in [x.lower() for x in data[name]]:
                    out = item + " steht schon auf der " + name + "."
                else:
                    data[name].append(item); _save(data)
                    out = item + " auf die " + name + " gesetzt. Jetzt " + str(len(data[name])) + " Einträge."
        elif action == "remove":
            lst = data.get(name, [])
            match = next((x for x in lst if x.lower() == item.lower()), None)
            if match:
                lst.remove(match); data[name] = lst; _save(data)
                out = match + " von der " + name + " gestrichen."
            else:
                out = item + " steht nicht auf der " + name + "."
        elif action == "show":
            lst = data.get(name, [])
            out = ("Deine " + name + " ist leer." if not lst
                   else "Auf der " + name + ": " + ", ".join(lst) + ".")
        elif action == "clear":
            data[name] = []; _save(data)
            out = "Die " + name + " wurde geleert."
        elif action == "all":
            names = [k for k, v in data.items() if v]
            out = ("Du hast keine Listen mit Einträgen." if not names
                   else "Deine Listen: " + ", ".join(n + " (" + str(len(data[n])) + ")" for n in names) + ".")
        else:
            out = "Unbekannte Listen-Aktion. Möglich: add, remove, show, clear, all."
    except Exception as e:
        return "Die Listen-Verwaltung ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            pass
    return out
