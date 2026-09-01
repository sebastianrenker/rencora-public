"""
Rencora Übersetzer — übersetzt Text in eine Zielsprache über Grok/Groq (spart Gemini-Tokens).
'übersetz das auf Englisch', 'wie sagt man X auf Französisch', 'übersetz alles was ich sage auf Englisch'.
Für den Dauer-Übersetzer sagst du z.B. 'Übersetzer-Modus Englisch' — dann übersetzt Rencora jede
weitere Äußerung, bis du 'Übersetzer aus' sagst (das steuert Rencora über wiederholte Aufrufe).
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""

PLUGIN = {
    "name": "translate",
    "description": (
        "Übersetzt Text in eine Zielsprache (via Grok/Groq). Nutze es bei: 'übersetz … auf Englisch', "
        "'wie sagt man … auf Spanisch', 'was heißt … auf Französisch', und im Übersetzer-Modus für "
        "jede Äußerung des Nutzers. Standard-Zielsprache Englisch."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Der zu übersetzende Text"},
            "target": {"type": "STRING", "description": "Zielsprache, z.B. 'Englisch', 'Französisch' (Standard Englisch)"},
        },
        "required": ["text"],
    },
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    text = (parameters.get("text") or "").strip()
    if not text:
        return "Was soll ich übersetzen?"
    target = (parameters.get("target") or "Englisch").strip()
    try:
        from plugins.grok import grok_complete, is_configured
        if is_configured():
            out = grok_complete(
                "Übersetze den folgenden Text präzise und natürlich ins " + target +
                ". Gib NUR die Übersetzung aus, ohne Anführungszeichen, ohne Erklärung:\n\n" + text,
                "Du bist ein professioneller Übersetzer.")
            if out:
                return out.strip()
    except Exception:
        pass
    # Ohne Grok: Rencora (Gemini) übersetzt selbst
    return "Übersetze bitte ins " + target + ": " + text
