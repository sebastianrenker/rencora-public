"""
Rencora device discovery — auto-detects devices on the home network.
Uses SSDP/UPnP (smart TVs incl. Fire TV, media renderers, routers, some printers) plus
the ARP table (count of active hosts). No hardware or config needed.

'welche geräte habe ich', 'scanne mein netzwerk', 'finde meine geräte'.
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import re
import socket
import subprocess
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

try:
    import requests
except Exception:
    requests = None

PLUGIN = {
    "name": "scan_devices",
    "description": (
        "Discover devices on the user's home network automatically (smart TVs, Fire TV, "
        "media players, routers, some printers) and count active hosts. Use for: "
        "'welche Geräte habe ich', 'scanne mein Netzwerk', 'finde meine Geräte', "
        "'was ist alles im Netzwerk'."
    ),
    "parameters": {"type": "OBJECT", "properties": {}, "required": []},
}


def _ssdp():
    msg = "\r\n".join([
        "M-SEARCH * HTTP/1.1", "HOST: 239.255.255.250:1900",
        'MAN: "ssdp:discover"', "MX: 2", "ST: ssdp:all", "", ""]).encode()
    found = {}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(3)
        s.sendto(msg, ("239.255.255.250", 1900))
        import time
        end = time.time() + 3
        while time.time() < end:
            try:
                data, addr = s.recvfrom(2048)
            except socket.timeout:
                break
            except Exception:
                break
            txt = data.decode("utf-8", "replace")
            loc = re.search(r"LOCATION:\s*(.+)", txt, re.I)
            server = re.search(r"SERVER:\s*(.+)", txt, re.I)
            ip = addr[0]
            entry = found.setdefault(ip, {"location": None, "server": None})
            if loc and not entry["location"]:
                entry["location"] = loc.group(1).strip()
            if server and not entry["server"]:
                entry["server"] = server.group(1).strip()
        s.close()
    except Exception:
        _swallow_log.debug("ignored error", exc_info=True)
    return found


def _friendly(location):
    if not location or requests is None:
        return None
    try:
        xml = requests.get(location, timeout=3).text
        fn = re.search(r"<friendlyName>(.*?)</friendlyName>", xml, re.I | re.S)
        mn = re.search(r"<modelName>(.*?)</modelName>", xml, re.I | re.S)
        name = (fn.group(1).strip() if fn else "") or (mn.group(1).strip() if mn else "")
        return name or None
    except Exception:
        return None


def _arp_count():
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=6,
                             creationflags=0x08000000).stdout
        return len(set(m for m in re.findall(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", out)))
    except Exception:
        return 0


def run(parameters: dict, player=None, session_memory=None) -> str:
    try:
        ssdp = _ssdp()
        names = []
        for ip, e in list(ssdp.items())[:20]:
            n = _friendly(e.get("location"))
            if not n and e.get("server"):
                n = e["server"].split("/")[0]
            names.append(n or ip)
        # de-dup, keep readable ones
        seen, uniq = set(), []
        for n in names:
            k = n.lower()
            if k not in seen:
                seen.add(k); uniq.append(n)
        hosts = _arp_count()
        parts = []
        if uniq:
            parts.append("Erkannte Geräte im Netzwerk: " + ", ".join(uniq[:12]) + ".")
        else:
            parts.append("Ich konnte per UPnP keine benannten Geräte auslesen.")
        if hosts:
            parts.append("Insgesamt sind etwa " + str(hosts) + " Geräte im lokalen Netzwerk aktiv.")
        out = " ".join(parts)
    except Exception as e:
        return "Der Netzwerk-Scan ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return out
