"""
Rencora Brain access — lets Rencora search everything it has indexed about the owner:
their Rencora code (purple) and their Claude Code data/files/prompts (orange). Use this
so Rencora really knows the owner's files and can help with coding.

Build/refresh the index in the /brain HUD (Scan) or ask to 'scanne mein Hirn'.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import sys
from pathlib import Path
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PLUGIN = {
    "name": "brain_search",
    "description": (
        "Search the owner's indexed knowledge base ('brain'): their code files, config, and "
        "their Claude Code data/prompts. Use to answer questions about the owner's files, look "
        "up code/prompts, or help with coding. actions: 'search' (needs query), 'stats' "
        "(how many neurons), 'scan' (rebuild the index). "
        "Trigger: 'such in meinem code/hirn nach X', 'was steht in Datei Y', 'hilf mir beim "
        "coden', 'scanne mein Hirn', 'was weißt du über meine Projekte/Claude-Daten'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "search | stats | scan"},
            "query": {"type": "STRING", "description": "What to search for (for action=search)"},
        },
        "required": ["action"],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "search").strip().lower()
    try:
        import brain_db
    except Exception as e:
        return "Das Brain-Modul ist nicht verfügbar: " + str(e)
    try:
        if action == "scan":
            c = brain_db.scan()
            out = ("Hirn neu indexiert: " + str(sum(c.values())) + " Neuronen ("
                   + ", ".join(k + ": " + str(v) for k, v in c.items()) + ").")
        elif action == "stats":
            s = brain_db.stats()
            bs = s.get("by_source", {})
            out = ("Im Hirn: " + str(s.get("total", 0)) + " Neuronen — Rencora "
                   + str(bs.get("rencora", 0)) + ", Claude " + str(bs.get("claude", 0)) + ".")
        else:
            q = (parameters.get("query") or "").strip()
            if not q:
                return "Wonach soll ich im Hirn suchen?"
            res = brain_db.search(q, 6)
            if not res:
                out = "Ich habe zu '" + q + "' nichts im Hirn gefunden. Vielleicht erst scannen."
            else:
                parts = []
                for r in res:
                    snip = (r.get("snippet") or "").replace("\n", " ")[:160]
                    parts.append(r["name"] + " [" + r["source"] + "]: " + snip)
                out = "Treffer im Hirn zu '" + q + "': " + " | ".join(parts)
    except Exception as e:
        return "Die Hirn-Suche ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out[:400])
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return out
