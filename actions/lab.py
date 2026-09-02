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


def _prompt(labels, mode, caption=""):
    objs = ", ".join([l for l in (labels or []) if l])
    parts = []
    if caption:
        parts.append("Automatische Bildbeschreibung der Kamera (englisch): \"" + caption + "\".")
    if objs:
        parts.append("Ein einfacher Objekt-Detektor rät zusätzlich (KANN FALSCH sein): " + objs + ".")
    ctx = " ".join(parts) if parts else "Vor der Kamera ist ein Objekt."
    base = (ctx + " Bestimme, was am wahrscheinlichsten zu sehen ist (auch Geld, Werkzeug, "
            "Elektronik, Bauteile). Widersprechen sich die Hinweise, vertraue der Bildbeschreibung. "
            "Gib IMMER eine konkrete beste Einschätzung ab und benenne das Objekt — frage NIEMALS "
            "nach weiteren Beschreibungen. Bleibt Unsicherheit, sag kurz, was es am ehesten ist. ")
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


def analyze(labels, mode="identify", caption=""):
    try:
        from plugins.grok import grok_complete, is_configured
        if not is_configured():
            return ""
        return (grok_complete(_prompt(labels, mode, caption), _SYS) or "").strip()
    except Exception:
        return ""


def _vision_prompt(mode):
    m = (mode or "identify").lower()
    lead = ("Auf dem Kamerabild ist ein Objekt/Bauteil/Gegenstand. Bestimme GENAU und konkret, "
            "was es ist — auch Geld/Geldscheine, Werkzeug, Elektronik, Bauteile. Antworte auf "
            "Deutsch und gib immer eine klare Antwort. ")
    if any(k in m for k in ("zerleg", "auseinander", "disassemb")):
        return lead + "Erkläre dann, wie man es sicher zerlegt: Werkzeug, Schritte, worauf achten."
    if any(k in m for k in ("bau", "zusammen", "assemb", "aufbau")):
        return lead + "Erkläre dann Schritt für Schritt, wie man es zusammenbaut/aufbaut."
    if any(k in m for k in ("analys", "analyze")):
        return lead + "Analysiere es technisch: Funktion, Eigenschaften/Werte, typische Probleme."
    return lead + "Sag knapp, was es ist, wofür es dient, und ein bis zwei nützliche Tipps."


def vision_analyze(img_bytes, mode="identify"):
    """Genaue Bild-Analyse via Gemini-Vision (nur auf Knopfdruck → sparsam). Retry bei
    transientem 503 (Überlastung). Leerer String bei endgültigem Fehler."""
    try:
        import io
        import time
        from google import genai
        from actions.file_processor import _get_api_key
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        client = genai.Client(api_key=_get_api_key())
        prompt = _vision_prompt(mode)
        last = None
        for attempt in range(3):
            try:
                # gemini-2.5-flash: aktuell verfügbar (flash-latest war überlastet)
                return (client.models.generate_content(
                    model="gemini-2.5-flash", contents=[prompt, img]).text or "").strip()
            except Exception as e:
                last = e
                if any(k in str(e) for k in ("503", "UNAVAILABLE", "overloaded", "high demand", "429", "RESOURCE_EXHAUSTED")):
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
        raise last
    except Exception:
        return ""


def save_labels(labels, caption=""):
    try:
        _CACHE.write_text(json.dumps({"labels": labels or [], "caption": caption or "", "at": time.time()},
                                     ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def load_state(max_age=120):
    """-> (labels, caption) des zuletzt von einer Kamera-Seite gepushten Zustands."""
    try:
        d = json.loads(_CACHE.read_text(encoding="utf-8"))
        if time.time() - d.get("at", 0) < max_age:
            return (d.get("labels", []), d.get("caption", ""))
    except Exception:
        pass
    return ([], "")


def load_labels(max_age=120):   # Rückwärtskompatibel
    return load_state(max_age)[0]
