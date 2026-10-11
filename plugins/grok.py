"""
Rencora ↔ Grok — offload heavy thinking to xAI's Grok to spread token usage across
providers. Rencora's live VOICE stays Gemini (only Gemini has real-time audio); Grok
does the reasoning/long generation and Gemini speaks the result in the same voice.

Needs an xAI API key in config/grok.json:  { "xai_api_key": "xai-...", "model": "grok-4" }
(get one at console.x.ai). The API is OpenAI-compatible.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
from pathlib import Path
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

try:
    import requests
except Exception:
    requests = None

_CFG = Path(__file__).resolve().parent.parent / "config" / "grok.json"

PLUGIN = {
    "name": "ask_grok",
    "description": (
        "Ask xAI's Grok for heavy reasoning, a second opinion, long text generation, or "
        "deep analysis — use this to SPREAD token usage across providers (saves Gemini tokens). "
        "Good for: complex problems, long explanations, brainstorming, code reasoning, research "
        "synthesis. You (Rencora) then speak Grok's answer in your normal voice. "
        "Trigger: 'frag Grok', 'lass Grok das machen', 'nutz Grok', long/complex tasks."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The full question/task to send to Grok"},
        },
        "required": ["prompt"],
    },
}


def _cfg():
    try:
        return json.loads(_CFG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def is_configured():
    c = _cfg()
    return bool((c.get("xai_api_key") or c.get("api_key") or "").strip())


def _provider():
    """Auto-detect provider from the API-key prefix so BOTH work out of the box:
    'gsk_' -> Groq (api.groq.com), 'xai-' -> xAI Grok (api.x.ai). Returns (url, model, key, name)."""
    c = _cfg()
    key = (c.get("xai_api_key") or c.get("api_key") or "").strip()
    model = (c.get("model") or "").strip()
    if key.startswith("gsk_"):
        # Groq (groq.com) — sehr schnell, OpenAI-kompatibel. 'grok-4' ist dort kein Modell.
        if not model or model.startswith("grok"):
            model = "openai/gpt-oss-120b"
        return ("https://api.groq.com/openai/v1/chat/completions", model, key, "Groq")
    return (c.get("endpoint") or "https://api.x.ai/v1/chat/completions", (model or "grok-4"), key, "Grok")


def grok_complete(prompt, system="Du bist ein praeziser, hilfreicher Assistent."):
    """Reusable: text completion from Grok/Groq. Returns the text, or None if not
    configured / fails. Used as an automatic fallback when Gemini is quota-limited."""
    if requests is None:
        return None
    url, model, key, _name = _provider()
    if not key:
        return None
    try:
        r = requests.post(url,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            json={"model": model, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}]},
            timeout=60)
        if r.status_code >= 400:
            return None
        out = (((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        return out or None
    except Exception:
        return None


def text_with_fallback(gemini_call, prompt, system="Du bist ein praeziser, hilfreicher Assistent."):
    """Run a Gemini text call; on ANY failure (esp. 429 quota / Denkaussetzer) fall back to
    Grok automatically. `gemini_call` is a 0-arg callable returning the text (may raise).
    Returns (text, source) where source is 'gemini' | 'grok' | 'none'."""
    try:
        txt = gemini_call()
        txt = (txt or "").strip() if isinstance(txt, str) else (getattr(txt, "text", "") or "").strip()
        if txt:
            return (txt, "gemini")
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)
    alt = grok_complete(prompt, system)
    return (alt, "grok") if alt else ("", "none")


def run(parameters: dict, player=None, session_memory=None) -> str:
    prompt = (parameters.get("prompt") or "").strip()
    if not prompt:
        return "Was soll ich Grok fragen?"
    if requests is None:
        return "Das Grok-Modul braucht das requests-Paket."
    url, model, key, name = _provider()
    if not key:
        return ("Grok ist noch nicht eingerichtet. Trage deinen API-Key in "
                "config/grok.json ein (xai_api_key), dann teile ich die Arbeit zwischen Gemini und Grok.")
    try:
        r = requests.post(url,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            json={"model": model, "messages": [
                {"role": "system", "content": "Du bist Rencora, ein praeziser, hilfreicher Assistent. Antworte klar und auf Deutsch."},
                {"role": "user", "content": prompt}]},
            timeout=60)
        if r.status_code == 401:
            return "Der API-Key wird abgelehnt — bitte in config/grok.json pruefen."
        if r.status_code >= 400:
            return name + "-Fehler (" + str(r.status_code) + "): " + r.text[:200]
        data = r.json()
        out = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not out:
            out = "Grok hat keine Antwort geliefert."
    except Exception as e:
        return "Grok nicht erreichbar: " + str(e)
    if player:
        try:
            player.write_log("JARVIS(Grok): " + out[:300])
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return out
