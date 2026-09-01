"""
Rencora WLAN-Wächter — sagt dem Nutzer proaktiv Bescheid, wenn das WLAN ausfällt
(egal an welchem der WLANs hier: es meldet immer das SSID, das im Ausfallmoment aktiv war),
wenn das WLAN zwar da ist aber das Internet weg ist, und wenn es wieder da ist.

Ein Hintergrund-Thread (Start beim Import; Rencora läuft dauerhaft) prüft alle ~15s per
`netsh wlan show interfaces` das verbundene WLAN + Signal und testet die Internet-Erreichbarkeit
(TCP zu 1.1.1.1:53). Zwei aufeinanderfolgende Fehlschläge = echter Ausfall (keine Fehlalarme
bei einem kurzen Blip). Ereignisse werden nach config/wifi_events.json geschrieben.

Sprachausgabe kommt über prime(player)/run(player).request_say. Tool `wifi` beantwortet
"Status vom WLAN" / "wann ging das WLAN aus" mit aktuellem Zustand + letzten Ausfällen.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import json
import socket
import subprocess
import threading
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

_FILE = Path(__file__).resolve().parent.parent / "config" / "wifi_events.json"
_BUD = Path(__file__).resolve().parent.parent / "config" / "net_budget.json"
_SAY = {"fn": None, "log": None}
_NO_WINDOW = 0x08000000
_INTERVAL = 15          # Sekunden zwischen den Prüfungen
_CONFIRM = 2            # so viele Fehlschläge in Folge = echter Ausfall
_MAX_EVENTS = 200

PLUGIN = {
    "name": "wifi",
    "description": (
        "WLAN-/Internet-Status, Ausfall-Historie UND Kindersicherung/Zeitbudget-Warnung (FRITZ!Box-Ticket). "
        "Rencora meldet Ausfälle von selbst und warnt rechtzeitig, bevor das Internet durch die "
        "Zeitbeschränkung abgeschaltet wird (dann braucht der Nutzer ein Ticket). Nutze das Tool bei: "
        "'Status vom WLAN', 'wann ist das WLAN ausgegangen', 'wann geht mein Internet aus', "
        "'wie lange hab ich noch Internet', 'ab wann brauche ich ein Ticket', "
        "'mein Internet geht um 22 Uhr aus' (set_cutoff), 'ich hab 2 Stunden Internet am Tag' (set_budget), "
        "'lern das selbst' (auto), 'ich hab ein Ticket geholt' (ticket_used), 'Warnung aus' (budget_off). "
        "actions: status | history | ticket (Restzeit/Budget) | set_cutoff (time HH:MM) | "
        "set_budget (minutes) | auto | ticket_used | budget_off."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "status | history | ticket | set_cutoff | set_budget | auto | ticket_used | budget_off"},
            "time": {"type": "STRING", "description": "Abschaltzeit HH:MM (für set_cutoff)"},
            "minutes": {"type": "INTEGER", "description": "Tages-Budget in Minuten (für set_budget)"},
        },
        "required": [],
    },
}


def prime(player):
    """Vom Plugin-Loader beim Start aufgerufen, damit der Wächter proaktiv sprechen kann."""
    _SAY["fn"] = getattr(player, "request_say", None)
    _SAY["log"] = getattr(player, "write_log", None)


def _iface():
    """(ssid, signal_pct, connected) des WLAN-Adapters via netsh; robust über DE/EN."""
    try:
        out = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                             capture_output=True, text=True, timeout=8,
                             creationflags=_NO_WINDOW, encoding="utf-8", errors="replace").stdout
    except Exception:
        return ("", None, None)  # netsh nicht nutzbar -> Zustand unbekannt
    ssid, signal, state = "", None, None
    for line in out.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip().lower()
        v = v.strip()
        if k == "ssid":                       # exakt "SSID", nicht "BSSID"
            ssid = v
        elif k.startswith("signal"):
            try:
                signal = int(v.replace("%", "").strip())
            except Exception:
                pass
        elif k in ("state", "status", "zustand"):
            state = v.lower()
    connected = bool(ssid) or (state is not None and ("connect" in (state or "") or "verbund" in (state or "")))
    return (ssid, signal, connected)


def _internet():
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            s = socket.create_connection((host, 53), timeout=2)
            s.close()
            return True
        except Exception:
            continue
    return False


def _probe():
    """-> ('online'|'nonet'|'offline', ssid, signal)."""
    ssid, signal, connected = _iface()
    if not connected:
        return ("offline", ssid, signal)
    return ("online" if _internet() else "nonet", ssid, signal)


def _load():
    try:
        return json.loads(_FILE.read_text(encoding="utf-8")).get("events", [])
    except Exception:
        return []


def _append(ev):
    events = _load()
    events.append(ev)
    try:
        _FILE.write_text(json.dumps({"events": events[-_MAX_EVENTS:]}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    except Exception:
        pass


def _announce(instruction, logline):
    log = _SAY.get("log")
    if log:
        try:
            log("JARVIS: " + logline)
        except Exception:
            pass
    say = _SAY.get("fn")
    if say:
        try:
            say(instruction)
        except Exception:
            pass


def _default_bud():
    return {"mode": "off", "cutoff": "", "budget_min": 0, "warn_before": [15, 5],
            "state": {"date": "", "used_sec": 0, "warned": [], "exhausted": False}}


def _load_bud():
    try:
        b = json.loads(_BUD.read_text(encoding="utf-8"))
        d = _default_bud()
        d.update(b)
        d["state"] = {**_default_bud()["state"], **(b.get("state") or {})}
        return d
    except Exception:
        return _default_bud()


def _save_bud(cfg):
    try:
        _BUD.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _learn_cutoff():
    """Häufigste Abschaltzeit (auf 5 Min gerundet) aus der Ausfall-Historie; braucht >=2 Treffer."""
    times = []
    for e in _load():
        if e.get("type") in ("down", "nonet"):
            hm = e.get("at", "")[11:16]
            if len(hm) == 5:
                h, m = int(hm[:2]), int(hm[3:])
                m = (m // 5) * 5
                times.append(f"{h:02d}:{m:02d}")
    if not times:
        return ""
    hm, n = Counter(times).most_common(1)[0]
    return hm if n >= 2 else ""


def _remaining(cfg, online):
    """-> (remaining_min | None, cutoff_hm | None). Positiv = so viel Zeit bleibt."""
    mode = cfg.get("mode", "off")
    now = datetime.now()
    if mode in ("time", "auto"):
        hm = cfg.get("cutoff") if mode == "time" else _learn_cutoff()
        if not hm or ":" not in hm:
            return (None, None)
        h, m = int(hm[:2]), int(hm[3:5])
        cutoff = now.replace(hour=h, minute=m, second=0, microsecond=0)
        return ((cutoff - now).total_seconds() / 60.0, hm)
    if mode == "budget":
        if not online:
            return (None, None)
        rem = cfg.get("budget_min", 0) - cfg["state"].get("used_sec", 0) / 60.0
        return (rem, (now + timedelta(minutes=max(rem, 0))).strftime("%H:%M"))
    return (None, None)


def _budget_check(state):
    """Jede Runde: Nutzung zählen (Budget-Modus) + rechtzeitig vor der Abschaltung warnen."""
    cfg = _load_bud()
    if cfg.get("mode", "off") == "off":
        return
    today = datetime.now().date().isoformat()
    st = cfg["state"]
    if st.get("date") != today:
        st.update({"date": today, "used_sec": 0, "warned": [], "exhausted": False})
    online = (state == "online")
    if cfg["mode"] == "budget" and online:
        st["used_sec"] = st.get("used_sec", 0) + _INTERVAL
    rem, hm = _remaining(cfg, online)
    if rem is not None and (online or cfg["mode"] in ("time", "auto")):
        warn = sorted(cfg.get("warn_before", [15, 5]), reverse=True)
        if 0 < rem <= max(warn):
            for t in warn:
                if 0 < rem <= t and t not in st["warned"]:
                    st["warned"].append(t)
                    _announce(f"Warne den Nutzer freundlich, dass sein Internet in etwa {t} Minuten "
                              f"(gegen {hm}) durch die Kindersicherung abgeschaltet wird und er sich "
                              f"jetzt ein Ticket holen sollte.",
                              f"Internet-Warnung: in ~{t} Min Schluss (gegen {hm}) — Ticket holen.")
                    break
        elif -2 <= rem <= 0 and not st.get("exhausted"):
            st["exhausted"] = True
            _announce("Sag dem Nutzer, dass sein Internet-Zeitbudget jetzt aufgebraucht ist und er ein "
                      "Ticket braucht, um weiter online zu sein.",
                      "Internet-Budget aufgebraucht — Ticket nötig.")
    _save_bud(cfg)


def _watch():
    prev = None          # letzter bestätigter Zustand
    fails = 0            # aufeinanderfolgende Nicht-online-Prüfungen
    pending = None       # noch nicht bestätigter neuer Zustand
    down_since = None    # Zeitpunkt des letzten Ausfalls (für Dauerangabe)
    last_ssid = ""
    time.sleep(8)        # erst kurz warten, bis Netz beim Start steht
    while True:
        try:
            state, ssid, signal = _probe()
            if ssid:
                last_ssid = ssid
            _budget_check(state)
            if state == "online":
                if prev in ("offline", "nonet"):
                    mins = ""
                    if down_since:
                        d = int((time.time() - down_since) / 60)
                        mins = f" (war etwa {d} Minute{'n' if d != 1 else ''} weg)" if d >= 1 else " (kurz weg)"
                    _append({"type": "up", "ssid": last_ssid, "at": datetime.now().isoformat(timespec="seconds"),
                             "signal": signal})
                    _announce(f"Sag dem Nutzer kurz, dass das WLAN '{last_ssid or 'hier'}' wieder da ist{mins}.",
                              f"WLAN '{last_ssid}' wieder online{mins}.")
                    down_since = None
                prev, fails, pending = "online", 0, None
            else:
                # nicht online: erst nach _CONFIRM Prüfungen als Ausfall bestätigen
                fails += 1
                pending = state
                if fails >= _CONFIRM and prev != pending:
                    now = datetime.now().strftime("%H:%M")
                    down_since = time.time()
                    if pending == "offline":
                        _append({"type": "down", "ssid": last_ssid, "at": datetime.now().isoformat(timespec="seconds")})
                        _announce(f"Sag dem Nutzer, dass das WLAN '{last_ssid or 'hier'}' gerade um {now} ausgefallen ist.",
                                  f"WLAN '{last_ssid}' ausgefallen um {now}.")
                    else:  # nonet: WLAN da, Internet weg
                        _append({"type": "nonet", "ssid": last_ssid, "at": datetime.now().isoformat(timespec="seconds"),
                                 "signal": signal})
                        _announce(f"Sag dem Nutzer, dass das WLAN '{last_ssid or 'hier'}' zwar verbunden ist, "
                                  f"aber seit {now} kein Internet hat.",
                                  f"WLAN '{last_ssid}' ohne Internet seit {now}.")
                    prev = pending
        except Exception:
            pass
        time.sleep(_INTERVAL)


threading.Thread(target=_watch, daemon=True).start()


def _fmt(ev):
    t = ev.get("at", "")[:16].replace("T", " ")
    kind = {"down": "ausgefallen", "nonet": "ohne Internet", "up": "wieder da"}.get(ev.get("type"), ev.get("type"))
    return f"{t} — {ev.get('ssid') or '?'}: {kind}"


def run(parameters: dict, player=None, session_memory=None) -> str:
    if player is not None:
        _SAY["fn"] = getattr(player, "request_say", None)
        _SAY["log"] = getattr(player, "write_log", None)
    action = (parameters.get("action") or "status").strip().lower()
    if action == "history":
        events = _load()[-8:]
        return "Noch keine WLAN-Ausfälle aufgezeichnet." if not events else \
            "Letzte WLAN-Ereignisse:\n" + "\n".join(_fmt(e) for e in reversed(events))

    # --- Kindersicherung / Zeitbudget / Ticket ---
    if action in ("set_cutoff", "set_budget", "auto", "ticket_used", "budget_off", "ticket"):
        cfg = _load_bud()
        if action == "set_cutoff":
            t = (parameters.get("time") or "").strip()
            if ":" not in t:
                return "Um welche Uhrzeit (HH:MM) wird dein Internet abgeschaltet?"
            cfg["mode"] = "time"; cfg["cutoff"] = t[:5]
            _save_bud(cfg)
            return f"Alles klar — ich warne dich rechtzeitig, bevor dein Internet um {t[:5]} abgeschaltet wird (Ticket nötig)."
        if action == "set_budget":
            m = parameters.get("minutes")
            try:
                m = int(m)
            except Exception:
                return "Wie viele Minuten Internet hast du pro Tag?"
            cfg["mode"] = "budget"; cfg["budget_min"] = m
            cfg["state"] = {"date": "", "used_sec": 0, "warned": [], "exhausted": False}
            _save_bud(cfg)
            return f"Notiert: {m} Minuten Internet pro Tag. Ich warne dich, bevor das Budget aufgebraucht ist."
        if action == "auto":
            cfg["mode"] = "auto"; _save_bud(cfg)
            hm = _learn_cutoff()
            return ("Ich lerne die Abschaltzeit jetzt selbst aus den Ausfällen und warne dich vorher. "
                    + (f"Bisher sieht es nach ~{hm} aus." if hm else "Ich brauche noch ein paar Tage Daten dafür."))
        if action == "budget_off":
            cfg["mode"] = "off"; _save_bud(cfg)
            return "Kindersicherungs-Warnung ist aus."
        if action == "ticket_used":
            cfg["state"]["used_sec"] = max(0, cfg["state"].get("used_sec", 0) - 45 * 60)
            cfg["state"]["warned"] = []; cfg["state"]["exhausted"] = False
            _save_bud(cfg)
            return "Ticket verbucht — plus 45 Minuten. Ich melde mich wieder, bevor die Zeit alle ist."
        # action == "ticket": Restzeit melden
        state, _s, _sig = _probe()
        rem, hm = _remaining(cfg, state == "online")
        if cfg.get("mode", "off") == "off":
            return ("Es ist keine Zeitbeschränkung eingestellt. Sag mir z.B. 'mein Internet geht um 22 Uhr aus' "
                    "oder 'ich hab 2 Stunden Internet am Tag', dann warne ich dich rechtzeitig.")
        if rem is None:
            return "Ich kann die Restzeit gerade nicht bestimmen (Modus aktiv, aber keine Zeit/kein Budget gesetzt)."
        rem = int(rem)
        if rem <= 0:
            return f"Deine Internet-Zeit ist aufgebraucht — du brauchst jetzt ein Ticket."
        h, m = divmod(rem, 60)
        dur = (f"{h} Std {m} Min" if h else f"{m} Min")
        return f"Du hast noch etwa {dur} Internet (bis ~{hm}), dann brauchst du ein Ticket."

    # status
    state, ssid, signal = _probe()
    label = {"online": "verbunden mit Internet", "nonet": "verbunden, aber OHNE Internet",
             "offline": "KEIN WLAN verbunden"}[state]
    sig = f", Signal {signal}%" if signal is not None else ""
    events = _load()
    today = datetime.now().date().isoformat()
    outages_today = sum(1 for e in events if e.get("type") in ("down", "nonet") and e.get("at", "").startswith(today))
    last_down = next((e for e in reversed(events) if e.get("type") in ("down", "nonet")), None)
    extra = ""
    if outages_today:
        extra = f" Heute {outages_today} Ausfall/Ausfälle."
    if last_down:
        extra += " Zuletzt weg: " + _fmt(last_down) + "."
    bcfg = _load_bud()
    if bcfg.get("mode", "off") != "off":
        rem, hm = _remaining(bcfg, state == "online")
        if rem is not None:
            extra += (" Zeit-Budget aufgebraucht — Ticket nötig." if rem <= 0
                      else f" Noch ~{int(rem)} Min Internet (bis ~{hm}), dann Ticket.")
    out = f"WLAN '{ssid or '—'}': {label}{sig}.{extra}"
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            pass
    return out
