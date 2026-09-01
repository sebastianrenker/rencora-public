"""
Rencora document advisor — reads a document (photo from the camera, or a PDF/DOCX)
and explains it in plain language: what it is, what to fill in, deadlines, what to
expect. Acts like a doctor/lawyer EXPLAINER — always adds a disclaimer that it is not
a substitute for professional medical or legal advice.

Used by the /advisor HUD (uploads a photo/file, then calls this). Falls back to the
most recently uploaded file when no path is given.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
# The dashboard saves uploads to the first writable of these (see server _make_uploads_dir).
_UPLOAD_DIRS = [
    Path.home() / "Downloads" / "JARVIS Uploads",
    Path.home() / "Documents" / "JARVIS Uploads",
    _BASE / "uploads",
]

_DISCLAIMER = ("Hinweis: Das ist eine allgemeine, laienverständliche Erklärung und "
               "ersetzt keine ärztliche oder rechtliche Beratung.")

_ADVISOR = (
    "Du bist Rencora und erklärst dem Nutzer ein Dokument so, wie es ein hilfsbereiter "
    "Arzt oder Anwalt einem Laien erklären würde. Antworte auf Deutsch, klar und praktisch. "
    "Gehe auf diese Punkte ein, sofern erkennbar:\n"
    "1) Was ist das für ein Dokument / worum geht es?\n"
    "2) Was muss ich ausfüllen oder konkret tun?\n"
    "3) Welche Fristen, Termine oder Beträge sind wichtig?\n"
    "4) Was kommt auf mich zu / welche Folgen hat es?\n"
    "Halte es übersichtlich. Beende deine Antwort IMMER exakt mit diesem Satz: \"" + _DISCLAIMER + "\""
)

PLUGIN = {
    "name": "explain_document",
    "description": (
        "Read and explain a document (a photo of a form/letter, or a PDF/DOCX) in plain "
        "language — like a doctor or lawyer explaining it to a layperson: what it is, what to "
        "fill in, deadlines, what to expect. Use for: 'erklär mir dieses Dokument', 'was muss "
        "ich hier ausfüllen', 'was steht in diesem Brief/Formular', 'lies das Dokument'. "
        "Always includes a disclaimer. Without file_path it uses the most recently uploaded file."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to the document (optional; default = latest upload)"},
        },
        "required": [],
    },
}


def _latest_upload():
    files = []
    for d in _UPLOAD_DIRS:
        try:
            if d.exists():
                files += [p for p in d.iterdir() if p.is_file()]
        except Exception:
            pass
    if not files:
        return None
    try:
        return max(files, key=lambda p: p.stat().st_mtime)
    except Exception:
        return None


def _read_text(path):
    ext = path.suffix.lower().lstrip(".")
    if ext == "pdf":
        # PyMuPDF (fitz) ist vorhanden und robuster als pdfplumber.
        try:
            import fitz
            out = []
            doc = fitz.open(str(path))
            for page in doc[:20]:
                out.append(page.get_text() or "")
            doc.close()
            return "\n".join(out)[:20000]
        except Exception:
            return ""
    if ext in ("docx", "doc"):
        try:
            import docx
            return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)[:20000]
        except Exception:
            return ""
    if ext == "txt":
        try:
            return path.read_text(encoding="utf-8", errors="replace")[:20000]
        except Exception:
            return ""
    return ""


def _pdf_image(path):
    """Rendert Seite 1 eines PDFs als PIL-Bild — für gescannte PDFs ohne Textebene."""
    try:
        import io
        import fitz
        from PIL import Image
        doc = fitz.open(str(path))
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        doc.close()
        return img
    except Exception:
        return None


def run(parameters: dict, player=None, session_memory=None) -> str:
    fp = (parameters.get("file_path") or "").strip()
    path = Path(fp) if fp else _latest_upload()
    if not path or not Path(path).exists():
        return "Ich finde kein Dokument. Fotografiere es über den Advisor oder lade eine Datei hoch."
    path = Path(path)
    try:
        from actions.file_processor import _gemini_client
        model = _gemini_client()
    except Exception as e:
        return "Die Dokumentanalyse ist nicht verfügbar: " + str(e)

    def _gen(contents):
        import time
        last = None
        for attempt in range(3):                     # retry transient 503 / overload
            try:
                return model.generate_content(contents)
            except Exception as e:
                last = e
                if any(k in str(e) for k in ("503", "UNAVAILABLE", "overloaded", "high demand")):
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
        raise last

    ext = path.suffix.lower().lstrip(".")
    image_exts = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"}
    try:
        if ext in image_exts:
            from PIL import Image
            img = Image.open(path)
            resp = _gen([_ADVISOR, img])
            out = (resp.text or "").strip()
        else:
            text = _read_text(path)
            if not text.strip():
                # Gescanntes PDF ohne Textebene → erste Seite als Bild an die Vision geben.
                if ext == "pdf":
                    img = _pdf_image(path)
                    if img is None:
                        return "Ich konnte dieses PDF nicht lesen. Ein klares Foto der Seite hilft."
                    out = (_gen([_ADVISOR, img]).text or "").strip()
                else:
                    return ("Ich konnte den Text dieses Dokuments nicht lesen. "
                            "Schick mir ein Foto oder ein PDF/DOCX/TXT.")
            else:
                full = _ADVISOR + "\n\nDOKUMENT:\n" + text
                try:
                    out = (_gen([full]).text or "").strip()
                except Exception:
                    # Gemini-Quota/Überlastung → automatisch Grok/Groq (funktioniert für Text)
                    try:
                        from plugins.grok import grok_complete
                        out = (grok_complete(full, _ADVISOR) or "").strip()
                    except Exception:
                        out = ""
                    if not out:
                        raise
        if _DISCLAIMER not in out:
            out += "\n\n" + _DISCLAIMER
    except Exception as e:
        return "Die Dokumentanalyse ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out[:400])
        except Exception:
            pass
    return out
