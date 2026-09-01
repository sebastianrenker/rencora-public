"""
Rencora smart home — control lights/plugs/scenes by voice.
Config-driven so it works with almost anything (Home Assistant webhooks, Philips Hue
bridge, Tasmota, Shelly, IFTTT/webhook, ...): each device+action maps to an HTTP call.

config/smarthome.json:
{
  "devices": {
    "wohnzimmer licht": {
      "on":  {"method":"PUT","url":"http://<hue-bridge>/api/<key>/lights/1/state","json":{"on":true}},
      "off": {"method":"PUT","url":"http://<hue-bridge>/api/<key>/lights/1/state","json":{"on":false}}
    }
  }
}

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

_FILE = Path(__file__).resolve().parent.parent / "config" / "smarthome.json"

PLUGIN = {
    "name": "smart_home",
    "description": (
        "Control smart-home devices (lights, plugs, scenes) by voice: "
        "'mach das Wohnzimmerlicht an', 'schalt die Steckdose aus', 'Szene Kino', "
        "'Licht auf 30 Prozent'. actions: on | off | toggle | set (with value) | scene. "
        "device = the device or scene name."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "on | off | toggle | set | scene"},
            "device": {"type": "STRING", "description": "Device or scene name, e.g. 'Wohnzimmer Licht'"},
            "value": {"type": "STRING", "description": "Optional value (e.g. brightness 0-100) for action=set"},
        },
        "required": ["action", "device"],
    },
}


def _cfg():
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _match(devices, name):
    name = name.lower().strip()
    if name in devices:
        return name
    for k in devices:
        if name in k.lower() or k.lower() in name:
            return k
    return None


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "").strip().lower()
    device = (parameters.get("device") or "").strip()
    value = (parameters.get("value") or "").strip()
    cfg = _cfg()
    devices = cfg.get("devices", {})
    if not devices:
        return ("Es sind noch keine Smart-Home-Geräte eingerichtet. Sag mir, welche Geräte du hast "
                "(z.B. Philips Hue, Home Assistant, Tasmota), dann richte ich sie in config/smarthome.json ein.")
    if requests is None:
        return "Das Smart-Home-Modul braucht das requests-Paket."
    key = _match(devices, device)
    if not key:
        return "Ich kenne das Gerät '" + device + "' nicht. Bekannt: " + ", ".join(devices.keys()) + "."
    spec = devices[key].get(action)
    if not spec:
        return "Für " + key + " ist die Aktion '" + action + "' nicht eingerichtet."
    try:
        # allow {value} placeholder in url / json for action=set
        url = spec.get("url", "").replace("{value}", value)
        method = (spec.get("method") or "GET").upper()
        js = spec.get("json")
        if isinstance(js, str):
            js = json.loads(js.replace("{value}", value))
        r = requests.request(method, url, json=js, headers=spec.get("headers"), timeout=8)
        ok = r.status_code < 400
    except Exception as e:
        return "Konnte " + key + " nicht schalten: " + str(e)
    if not ok:
        return key + " hat nicht reagiert (Status " + str(r.status_code) + ")."
    verb = {"on": "eingeschaltet", "off": "ausgeschaltet", "toggle": "umgeschaltet",
            "set": "eingestellt", "scene": "aktiviert"}.get(action, "geschaltet")
    out = key + " " + verb + "."
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            pass
    return out
