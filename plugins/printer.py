"""
Rencora printer control — normal Windows printers AND Bambu Lab 3D printers.

Normal printers: list / status / print a document (via pywin32, already a dependency).
Bambu Lab:       status / pause / resume / stop over local MQTT (LAN mode).

Bambu needs config/printer.json:
    { "bambu": { "host": "192.168.x.x", "serial": "01Sxxxxxx", "access_code": "12345678" } }
Access-Code + LAN-Mode: on the printer under Settings > Network. Bambu control also
needs paho-mqtt (pip install paho-mqtt); normal printing does not.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
import os
import ssl
import time
from pathlib import Path

_CFG = Path(__file__).resolve().parent.parent / "config" / "printer.json"

PLUGIN = {
    "name": "printer_control",
    "description": (
        "Control printers. Use for ANY printing / printer request: normal paper/document "
        "printers AND the Bambu Lab 3D printer. "
        "actions: 'list' (show available printers), 'status' (default printer queue / job count), "
        "'print' (print a document - needs file_path), "
        "'bambu_status' (3D printer temps + progress), 'bambu_pause', 'bambu_resume', 'bambu_stop'. "
        "Trigger phrases: drucken, Drucker, Druckauftrag, Druckerstatus, Warteschlange, "
        "3D-Druck, Bambu, Druck pausieren/fortsetzen/stoppen."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING",
                       "description": "list | status | print | bambu_status | bambu_pause | bambu_resume | bambu_stop"},
            "file_path": {"type": "STRING", "description": "Path of the document to print (for action=print)"},
            "printer_name": {"type": "STRING", "description": "Optional target printer name (for action=print)"},
        },
        "required": ["action"],
    },
}

Q1, Q2 = "„", "“"  # German quotes, kept out of f-string delimiters


# --------------------------- normal Windows printers ---------------------------
def _normal_list():
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = [p[2] for p in win32print.EnumPrinters(flags)]
        default = ""
        try:
            default = win32print.GetDefaultPrinter()
        except Exception:
            pass
        if not printers:
            return "Ich finde keine installierten Drucker."
        marked = [(n + " (Standard)" if n == default else n) for n in printers]
        return "Verfuegbare Drucker: " + ", ".join(marked) + "."
    except ImportError:
        return "Drucker-Steuerung braucht pywin32 (pip install pywin32)."
    except Exception as e:
        return "Drucker konnten nicht gelesen werden: " + str(e)


def _normal_status():
    try:
        import win32print
        name = win32print.GetDefaultPrinter()
        h = win32print.OpenPrinter(name)
        try:
            jobs = win32print.EnumJobs(h, 0, -1, 1)
            info = win32print.GetPrinter(h, 2)
        finally:
            win32print.ClosePrinter(h)
        status = info.get("Status", 0)
        n = len(jobs)
        state = "bereit" if status == 0 else ("Statuscode " + str(status))
        head = "Standarddrucker " + Q1 + name + Q2 + " ist " + state + "."
        if n == 0:
            return head + " Keine Auftraege in der Warteschlange."
        titles = ", ".join(j.get("pDocument", "Dokument") for j in jobs[:3])
        return ("Standarddrucker " + Q1 + name + Q2 + " (" + state + "): "
                + str(n) + " Auftrag/Auftraege in der Warteschlange - " + titles + ".")
    except ImportError:
        return "Drucker-Steuerung braucht pywin32 (pip install pywin32)."
    except Exception as e:
        return "Druckerstatus nicht verfuegbar: " + str(e)


def _normal_print(file_path, printer_name=""):
    if not file_path:
        return "Welche Datei soll ich drucken? Bitte gib einen Dateipfad an."
    p = Path(os.path.expandvars(os.path.expanduser(file_path)))
    if not p.exists():
        return "Die Datei " + Q1 + str(file_path) + Q2 + " existiert nicht."
    try:
        import win32api, win32print
        if printer_name:
            win32api.ShellExecute(0, "printto", str(p), '"' + printer_name + '"', ".", 0)
            target = printer_name
        else:
            win32api.ShellExecute(0, "print", str(p), None, ".", 0)
            try:
                target = win32print.GetDefaultPrinter()
            except Exception:
                target = "Standarddrucker"
        return Q1 + p.name + Q2 + " wird an " + target + " gesendet."
    except ImportError:
        return "Drucken braucht pywin32 (pip install pywin32)."
    except Exception as e:
        return "Drucken fehlgeschlagen: " + str(e)


# ------------------------------- Bambu Lab (MQTT) -------------------------------
def _bambu_cfg():
    try:
        cfg = json.loads(_CFG.read_text(encoding="utf-8")).get("bambu", {})
    except Exception:
        return None
    if not cfg.get("host") or not cfg.get("serial") or not cfg.get("access_code"):
        return None
    return cfg


def _bambu_call(want_report=False, command=None):
    cfg = _bambu_cfg()
    if not cfg:
        return None, ("Der Bambu-Drucker ist noch nicht eingerichtet. Trage host, serial und "
                      "access_code in config/printer.json ein und aktiviere den LAN-Mode am Drucker.")
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        return None, "Fuer den Bambu-Drucker fehlt paho-mqtt (pip install paho-mqtt)."

    host, serial, code = cfg["host"], cfg["serial"], cfg["access_code"]
    report_topic = "device/" + serial + "/report"
    request_topic = "device/" + serial + "/request"
    result = {"report": None, "err": None}

    def on_connect(cli, u, flags, rc, *a):
        if rc == 0:
            cli.subscribe(report_topic)
            cli.publish(request_topic, json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}))
            if command is not None:
                cli.publish(request_topic, json.dumps(command))
        else:
            result["err"] = "MQTT-Verbindung abgelehnt (Code " + str(rc) + ") - Access-Code pruefen."

    def on_message(cli, u, msg):
        try:
            result["report"] = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            pass

    try:
        cli = mqtt.Client()
        cli.username_pw_set("bblp", code)
        cli.tls_set(cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        cli.tls_insecure_set(True)
        cli.on_connect = on_connect
        cli.on_message = on_message
        cli.connect(host, 8883, 10)
        cli.loop_start()
        deadline = time.time() + (6 if want_report else 3)
        while time.time() < deadline:
            if result["err"]:
                break
            if not want_report and command is not None:
                time.sleep(0.6)
                break
            if want_report and result["report"] is not None:
                break
            time.sleep(0.1)
        cli.loop_stop()
        cli.disconnect()
    except Exception as e:
        return None, "Bambu-Drucker nicht erreichbar: " + str(e)
    if result["err"]:
        return None, result["err"]
    return result["report"], None


def _bambu_status():
    report, err = _bambu_call(want_report=True)
    if err:
        return err
    if not report:
        return "Der Bambu-Drucker hat nicht rechtzeitig geantwortet."
    p = report.get("print", {})
    nozzle = p.get("nozzle_temper"); bed = p.get("bed_temper")
    pct = p.get("mc_percent"); rem = p.get("mc_remaining_time")
    stage = p.get("gcode_state", "?")
    state_de = {"RUNNING": "druckt", "IDLE": "im Leerlauf", "FINISH": "fertig",
                "PAUSE": "pausiert", "FAILED": "Fehler", "PREPARE": "bereitet vor"}.get(stage, stage)
    parts = ["Bambu-Drucker: " + state_de]
    if pct is not None:
        parts.append(str(pct) + "% fertig")
    if rem:
        parts.append("noch etwa " + str(rem) + " Minuten")
    if nozzle is not None and bed is not None:
        parts.append("Duese " + str(round(nozzle)) + " Grad, Bett " + str(round(bed)) + " Grad")
    return ", ".join(parts) + "."


def _bambu_cmd(command, ok_text):
    _, err = _bambu_call(command={"print": {"sequence_id": "0", "command": command}})
    return err or ok_text


# ------------------------------------ router ------------------------------------
def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "").strip().lower()
    try:
        if action == "list":
            out = _normal_list()
        elif action == "status":
            out = _normal_status()
        elif action == "print":
            out = _normal_print(parameters.get("file_path", ""), parameters.get("printer_name", ""))
        elif action == "bambu_status":
            out = _bambu_status()
        elif action == "bambu_pause":
            out = _bambu_cmd("pause", "Der 3D-Druck wurde pausiert.")
        elif action == "bambu_resume":
            out = _bambu_cmd("resume", "Der 3D-Druck wird fortgesetzt.")
        elif action == "bambu_stop":
            out = _bambu_cmd("stop", "Der 3D-Druck wurde gestoppt.")
        else:
            out = ("Unbekannte Drucker-Aktion. Moeglich: list, status, print, "
                   "bambu_status, bambu_pause, bambu_resume, bambu_stop.")
    except Exception as e:
        return "Die Drucker-Steuerung ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            pass
    return out
