"""
Rencora WhatsApp-Vorleser — liest NEU eintreffende WhatsApp-Nachrichten laut vor, aber nur
wenn der Nutzer es einschaltet (Tool/Knopf). Kein WhatsApp-Login nötig: es liest die
Windows-Benachrichtigungen (Toasts) der WhatsApp-App über den UserNotificationListener mit.

Voraussetzungen:
  - WhatsApp-Desktop installiert, Benachrichtigungen an.
  - Einmalig: Windows-Einstellungen → Datenschutz → Benachrichtigungen → Zugriff erlauben
    (Rencora fragt den Zugriff beim ersten Aktivieren an).

Aktivieren per Sprache/Knopf ("lies WhatsApp vor"), Backlog wird übersprungen — es werden nur
Nachrichten vorgelesen, die NACH dem Einschalten ankommen. Engine Mark-LI/FatihMakes CC BY-NC.
"""
import asyncio
import os
import re
import subprocess
import threading
import time
import urllib.parse

_SAY = {"fn": None, "log": None}
_STATE = {"on": False, "thread": None, "last_sender": ""}


def _set_clipboard(text):
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
                       input=text, text=True, timeout=8, creationflags=0x08000000)
        return True
    except Exception:
        return False

PLUGIN = {
    "name": "whatsapp",
    "description": (
        "Neue WhatsApp-Nachrichten laut vorlesen, sobald sie eintreffen — nur auf Wunsch. "
        "Nutze es bei: 'lies mir WhatsApp vor', 'WhatsApp-Nachrichten vorlesen', 'sag mir neue WhatsApp', "
        "'WhatsApp-Vorlesen an/aus', 'stopp WhatsApp'. "
        "Zum Antworten: 'antworte X mit …', 'schreib zurück …', 'antworte dem letzten …'. "
        "actions: 'on' (ab jetzt neue Nachrichten vorlesen), 'off' (stoppen), 'status', "
        "'reply' (Antwort vorbereiten — needs text; optional contact = Name/Nummer)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "on | off | status | reply"},
            "text": {"type": "STRING", "description": "Antworttext für action=reply"},
            "contact": {"type": "STRING", "description": "Empfänger (Name oder Telefonnummer) für action=reply; leer = letzter Absender"},
        },
        "required": [],
    },
}


def prime(player):
    _SAY["fn"] = getattr(player, "request_say", None)
    _SAY["log"] = getattr(player, "write_log", None)


def _say(instruction, logline=None):
    if _SAY.get("log") and logline:
        try: _SAY["log"]("JARVIS: " + logline)
        except Exception: pass
    if _SAY.get("fn"):
        try: _SAY["fn"](instruction)
        except Exception: pass


def _ns():
    """Notification-Namespaces via winsdk (bevorzugt) oder winrt (Fallback)."""
    try:
        from winsdk.windows.ui.notifications.management import (
            UserNotificationListener, UserNotificationListenerAccessStatus)
        from winsdk.windows.ui.notifications import NotificationKinds, KnownNotificationBindings
    except Exception:
        from winrt.windows.ui.notifications.management import (
            UserNotificationListener, UserNotificationListenerAccessStatus)
        from winrt.windows.ui.notifications import NotificationKinds, KnownNotificationBindings
    return (UserNotificationListener, UserNotificationListenerAccessStatus,
            NotificationKinds, KnownNotificationBindings)


async def _fetch():
    """-> (access_ok, [(id, appname, [texts]), ...]).  access_ok False = kein Zugriff."""
    (UserNotificationListener, UserNotificationListenerAccessStatus,
     NotificationKinds, KnownNotificationBindings) = _ns()
    listener = UserNotificationListener.current
    status = await listener.request_access_async()
    if status != UserNotificationListenerAccessStatus.ALLOWED:
        return (False, [])
    notes = await listener.get_notifications_async(NotificationKinds.TOAST)
    out = []
    for n in notes:
        try:
            app = (n.app_info.display_info.display_name or "")
        except Exception:
            app = ""
        if "whatsapp" not in app.lower():
            continue
        texts = []
        try:
            binding = n.notification.visual.get_binding(KnownNotificationBindings.get_toast_generic())
            if binding:
                for el in binding.get_text_elements():
                    try: texts.append(el.text)
                    except Exception: pass
        except Exception:
            pass
        out.append((int(n.id), app, texts))
    return (True, out)


def _poll():
    try:
        return asyncio.run(_fetch())
    except Exception as e:
        return (None, str(e))


def _watch():
    seen = set()
    first = True
    while _STATE["on"]:
        ok, data = _poll()
        if ok is False:
            _say("Sag dem Nutzer, dass Rencora keinen Zugriff auf die Windows-Benachrichtigungen hat. "
                 "Er soll ihn in den Windows-Einstellungen unter Datenschutz und Sicherheit, "
                 "Benachrichtigungen, erlauben.",
                 "WhatsApp-Vorlesen: Benachrichtigungszugriff fehlt.")
            _STATE["on"] = False
            break
        if ok is None:
            time.sleep(6); continue          # transienter Fehler → weiter versuchen
        for nid, app, texts in data:
            if nid in seen:
                continue
            seen.add(nid)
            if first:
                continue                      # Backlog beim Einschalten überspringen
            sender = texts[0] if texts else "Unbekannt"
            body = texts[1] if len(texts) > 1 else (texts[0] if texts else "")
            _STATE["last_sender"] = sender
            _say(f"Lies dem Nutzer diese neue WhatsApp-Nachricht ruhig vor — von {sender}: {body}",
                 f"WhatsApp von {sender}: {body[:80]}")
        first = False
        time.sleep(4)


def run(parameters: dict, player=None, session_memory=None) -> str:
    if player is not None:
        prime(player)
    action = (parameters.get("action") or "status").strip().lower()

    if action in ("on", "an", "start"):
        if _STATE["on"]:
            return "WhatsApp-Vorlesen läuft schon — ich sage dir neue Nachrichten an."
        _STATE["on"] = True
        t = threading.Thread(target=_watch, daemon=True)
        _STATE["thread"] = t
        t.start()
        return ("Alles klar — ab jetzt lese ich dir neue WhatsApp-Nachrichten vor, sobald sie ankommen. "
                "Sag 'WhatsApp aus', um es zu stoppen.")
    if action in ("off", "aus", "stop", "stopp"):
        _STATE["on"] = False
        return "WhatsApp-Vorlesen ist aus."

    if action in ("reply", "antworten", "antwort"):
        text = (parameters.get("text") or "").strip()
        if not text:
            return "Was soll ich antworten?"
        contact = (parameters.get("contact") or "").strip()
        num = re.sub(r"[^\d+]", "", contact)
        try:
            if num and len(num) >= 6:
                os.startfile("whatsapp://send?phone=" + urllib.parse.quote(num) +
                             "&text=" + urllib.parse.quote(text))
                return (f"Ich habe WhatsApp mit deiner Nachricht an {contact} vorbereitet — du musst nur "
                        f"noch auf Senden tippen. (Aus Sicherheit sende ich nicht selbst.)")
            _set_clipboard(text)
            try:
                os.startfile("whatsapp://")
            except Exception:
                pass
            who = contact or _STATE.get("last_sender") or "den passenden Chat"
            return (f"Deine Antwort liegt in der Zwischenablage und WhatsApp ist offen — öffne {who}, "
                    f"füge sie mit Strg+V ein und sende. (Aus Sicherheit sende ich nicht automatisch.)")
        except Exception as e:
            return "Konnte WhatsApp nicht öffnen: " + str(e)
    return ("WhatsApp-Vorlesen ist " + ("AN" if _STATE["on"] else "AUS") +
            ". Sag 'lies mir WhatsApp vor', um es einzuschalten.")
