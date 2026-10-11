"""
Rencora Vision — beschreibt, was die Kamera sieht (Gemini-Vision). Gemeinsam genutzt von:
  - /api/vision      (SCAN-Knopf auf Tisch/Holo: aktuelles Bild -> Beschreibung)
  - /api/vision-frame (Kamera-Seiten pushen regelmäßig den aktuellen Frame)
  - plugins/look.py  (Sprache 'was siehst du' -> beschreibt den zuletzt gepushten Frame)

Der zuletzt gepushte Frame liegt in FRAME_PATH, damit Sprach-Anfragen ein aktuelles Bild
haben, ohne dass der Server mit dem Browser um die Webcam kämpft.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import io
import time
from pathlib import Path
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

FRAME_PATH = Path(__file__).resolve().parent.parent / "config" / "vision_last.jpg"

_DEFAULT_Q = ("Beschreibe knapp und präzise auf Deutsch, was auf diesem Kamerabild zu sehen ist: "
              "Objekte, grob welche Szene, sichtbarer Text/Schrift und relevante Details. "
              "Sei konkret, aber halte dich kurz.")


def describe_image(image_bytes: bytes, question: str = "") -> str:
    from actions.file_processor import _gemini_client
    from PIL import Image
    model = _gemini_client()
    img = Image.open(io.BytesIO(image_bytes))
    q = (question or "").strip()
    prompt = (_DEFAULT_Q + "\n\nBeantworte zusätzlich diese Frage direkt: " + q) if q else _DEFAULT_Q
    resp = model.generate_content([prompt, img])
    return (getattr(resp, "text", "") or "").strip() or "Ich konnte auf dem Bild nichts Eindeutiges erkennen."


def save_frame(image_bytes: bytes) -> None:
    try:
        FRAME_PATH.write_bytes(image_bytes)
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)


def latest_frame_age() -> float:
    """Sekunden seit dem letzten gecachten Frame, oder -1 wenn keiner existiert."""
    try:
        return time.time() - FRAME_PATH.stat().st_mtime
    except Exception:
        return -1.0


def describe_latest(question: str = "") -> str:
    if not FRAME_PATH.exists():
        return ""
    return describe_image(FRAME_PATH.read_bytes(), question)


def decode_dataurl(data_url: str) -> bytes:
    """'data:image/jpeg;base64,XXXX' (oder reines base64) -> bytes. b'' bei Fehler."""
    import base64
    if not data_url:
        return b""
    try:
        s = data_url.split(",", 1)[1] if data_url.startswith("data:") else data_url
        return base64.b64decode(s)
    except Exception:
        return b""
