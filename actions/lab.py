"""
Rencora Objekt-Labor — erklärt/analysiert, was die Kamera erkannt hat (Bauteile, Technik,
Alltagsgegenstände). Die Erkennung selbst läuft KOSTENLOS im Browser (TensorFlow.js); hier
kommt nur die textliche Analyse via Grok/Groq (ebenfalls kostenlos, kein Gemini-Kontingent).
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import json
import time
from pathlib import Path

_CACHE = Path(__file__).resolve().parent.parent / "config" / "lab_last.json"

_SYS = ("Du bist Rencora, ein technischer Experte, der Bauteile, Technik und Alltagsgegenstände "
        "praxisnah erklärt. Antworte klar, konkret und auf Deutsch.")


def _prompt(labels, mode):
    objs = ", ".join([l for l in (labels or []) if l]) or "das Objekt vor der Kamera"
    base = "Vor der Kamera ist/sind: " + objs + ". "
    m = (mode or "identify").lower()
    if any(k in m for k in ("zerleg", "disassemb", "auseinander")):
        return base + ("Erkläre praxisnah, wie man das sicher zerlegt/auseinanderbaut: benötigtes "
                       "Werkzeug, Reihenfolge der Schritte, und worauf man achten muss (Sicherheit).")
    if any(k in m for k in ("bau", "assemb", "zusammen", "aufbau")):
        return base + "Erkläre Schritt für Schritt, wie man das zusammenbaut bzw. aufbaut."
    if any(k in m for k in ("analys", "analyze")):
        return base + ("Analysiere es technisch: Was ist es, wofür dient es, wie funktioniert es, "
                       "wichtige Eigenschaften/Werte und typische Probleme.")
    return base + ("Sag knapp und praktisch, was das ist (Bauteil / Technik / Gegenstand), wofür es "
                   "dient und ein bis zwei nützliche Hinweise.")


def analyze(labels, mode="identify"):
    try:
        from plugins.grok import grok_complete, is_configured
        if not is_configured():
            return ""
        return (grok_complete(_prompt(labels, mode), _SYS) or "").strip()
    except Exception:
        return ""


def save_labels(labels):
    try:
        _CACHE.write_text(json.dumps({"labels": labels or [], "at": time.time()}, ensure_ascii=False),
                          encoding="utf-8")
    except Exception:
        pass


def load_labels(max_age=120):
    try:
        d = json.loads(_CACHE.read_text(encoding="utf-8"))
        if time.time() - d.get("at", 0) < max_age:
            return d.get("labels", [])
    except Exception:
        pass
    return []
