"""
Rencora interface opener — opens Rencora's screens by voice.
'öffne den 3D-Tester', 'zeig die Leinwand', 'mach den Tisch auf', 'Startzentrale'.

Opens the surface as an app window, already logged in via the localhost /local route.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import os
import shutil
import subprocess
import urllib.parse
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

PLUGIN = {
    "name": "open_interface",
    "description": (
        "Open one of Rencora's visual screens on this computer. Use when the user says: "
        "'öffne/zeig/mach auf/starte' + one of: 3D-Tester/3D-Objekte/Hologramm-3D, "
        "Tisch/Bedienfläche, Leinwand/Anzeige, Startzentrale/Home/Menü, Panel/Konsole, "
        "Info-Wall/Wetter/Nachrichten, Globus/Weltkugel/Erde/Satellitenkarte, Brain, Advisor, "
        "Fire-TV, Fernbedienung, Einstellungen. "
        "surface: one of  home | desk | stage | 3d | panel | wall | globe | brain | advisor | tv | remote | settings."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "surface": {"type": "STRING", "description": "home | desk | stage | 3d | panel | wall | globe | brain | advisor | tv | remote | settings"},
        },
        "required": ["surface"],
    },
}

_ROUTES = {
    "home": "/home", "start": "/home", "startzentrale": "/home", "menu": "/home", "menü": "/home",
    "desk": "/desk", "tisch": "/desk",
    "stage": "/stage", "leinwand": "/stage", "anzeige": "/stage",
    "3d": "/holo3d", "3d-tester": "/holo3d", "tester": "/holo3d", "holo3d": "/holo3d", "objekt": "/holo3d", "modelle": "/holo3d",
    "panel": "/holo", "konsole": "/holo", "holo": "/holo",
    "wall": "/wall", "info-wall": "/wall", "infowall": "/wall", "wetter": "/wall", "nachrichten": "/wall", "news": "/wall", "aufgaben": "/wall",
    "globe": "/globe", "globus": "/globe", "weltkugel": "/globe", "erde": "/globe", "satellit": "/globe", "satellitenkarte": "/globe", "karte": "/globe",
    "globus-vollbild": "/globe?ambient=1", "globus-ambient": "/globe?ambient=1", "ambient": "/globe?ambient=1", "vollbild": "/globe?ambient=1", "beamer": "/globe?ambient=1",
    "status": "/status", "systemstatus": "/status", "diagnose": "/status", "zustand": "/status",
    "lab": "/lab", "labor": "/lab", "objektlabor": "/lab", "objekt-labor": "/lab", "scanner": "/lab", "objekt": "/lab", "bauteil": "/lab", "bauteile": "/lab",
    "advisor": "/advisor", "dokument": "/advisor", "berater": "/advisor", "arzt": "/advisor", "anwalt": "/advisor", "formular": "/advisor",
    "tv": "/tv", "fernseher": "/tv", "firetv": "/tv",
    "brain": "/brain", "hirn": "/brain", "gehirn": "/brain", "wissen": "/brain",
    "remote": "/remote", "fernbedienung": "/remote", "steuerung": "/remote", "steuern": "/remote",
    "settings": "/settings", "einstellungen": "/settings", "optionen": "/settings",
}


def _find_browser():
    for c in ("chrome.exe", "chrome", "msedge.exe", "msedge"):
        p = shutil.which(c)
        if p:
            return p
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if os.path.exists(p):
            return p
    return None


def run(parameters: dict, player=None, session_memory=None) -> str:
    key = (parameters.get("surface") or "home").strip().lower()
    route = _ROUTES.get(key, "/home")
    url = "http://127.0.0.1:8000/local?to=" + urllib.parse.quote(route, safe="")
    names = {"/home": "die Startzentrale", "/desk": "den Tisch", "/stage": "die Leinwand",
             "/holo3d": "den 3D-Tester", "/holo": "das Panel", "/advisor": "den Advisor",
             "/tv": "das TV-HUD", "/brain": "das Brain", "/remote": "die Fernbedienung",
             "/settings": "die Einstellungen", "/wall": "die Info-Wall", "/globe": "den Globus",
             "/globe?ambient=1": "den Globus im Ambient-Vollbild", "/status": "den Systemstatus",
             "/lab": "das Objekt-Labor"}
    try:
        b = _find_browser()
        if b:
            subprocess.Popen([b, "--app=" + url, "--start-fullscreen", "--new-window"],
                             creationflags=0x00000008)     # DETACHED
        else:
            import webbrowser
            webbrowser.open(url)
        out = "Ich öffne " + names.get(route, "die Oberfläche") + "."
    except Exception as e:
        return "Konnte die Oberfläche nicht öffnen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return out
