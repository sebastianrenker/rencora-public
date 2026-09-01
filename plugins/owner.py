"""
Rencora owner settings — lets the current user set who they are (name, GitHub,
assistant name). Anyone using Rencora can register themselves as the owner.

Writes config/owner.json. Name/GitHub take effect immediately; the spoken persona
name updates on the next start.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
from pathlib import Path

_CFG = Path(__file__).resolve().parent.parent / "config" / "owner.json"

PLUGIN = {
    "name": "set_owner",
    "description": (
        "Set or update who the owner/creator of this Rencora is. Use when the user says things "
        "like 'ich bin <Name>', 'merk dir dass ich <Name> bin', 'mein GitHub ist <x>', "
        "'nenn dich <Name>' (assistant name), 'du gehörst mir', or wants to change the owner/identity."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The owner's full name"},
            "github": {"type": "STRING", "description": "The owner's GitHub username (optional)"},
            "assistant_name": {"type": "STRING", "description": "What the assistant should be called (optional, e.g. Rencora)"},
            "role": {"type": "STRING", "description": "The owner's role/title (optional)"},
        },
        "required": [],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    try:
        cur = {}
        try:
            cur = json.loads(_CFG.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        changed = []
        for key in ("name", "github", "assistant_name", "role"):
            v = (parameters.get(key) or "").strip()
            if v:
                cur[key] = v
                changed.append(key)
        if not changed:
            return "Sag mir, wie du heißt (und optional GitHub), dann trage ich dich als Besitzer ein."
        cur.setdefault("notes", "Besitzer dieses Rencora.")
        _CFG.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        name = cur.get("name", "der neue Besitzer")
        out = "Verstanden. Ich habe " + name + " als Besitzer gespeichert."
        if "assistant_name" in changed:
            out += " Mein Name wird ab dem nächsten Start " + cur["assistant_name"] + " sein."
    except Exception as e:
        return "Konnte den Besitzer nicht speichern: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            pass
    return out
