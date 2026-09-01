"""
Rencora Info-Wall Datenquellen — Wetter (Open-Meteo, kein Key) und News (RSS). Für das
holografische Wand-Display (/wall), das wie ConceptBytes' JARVIS-Projektor Wetter/News/Karte
zeigt. Nur Standardbibliothek, keine zusätzlichen Pakete.

config/wall.json: { "city": "...", "lat": 52.52, "lon": 13.405, "news_rss": "..." }
Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — siehe NOTICE.md.
"""
import json
import re
import urllib.request
from pathlib import Path

_CFG = Path(__file__).resolve().parent.parent / "config" / "wall.json"
_UA = {"User-Agent": "Mozilla/5.0 (Rencora Info-Wall)"}

# WMO weather codes -> (deutsche Beschreibung, Emoji)
_WMO = {
    0: ("Klar", "☀️"), 1: ("Überwiegend klar", "🌤️"), 2: ("Teils bewölkt", "⛅"), 3: ("Bewölkt", "☁️"),
    45: ("Nebel", "🌫️"), 48: ("Reifnebel", "🌫️"),
    51: ("Leichter Niesel", "🌦️"), 53: ("Niesel", "🌦️"), 55: ("Starker Niesel", "🌧️"),
    56: ("Gefr. Niesel", "🌧️"), 57: ("Gefr. Niesel", "🌧️"),
    61: ("Leichter Regen", "🌦️"), 63: ("Regen", "🌧️"), 65: ("Starker Regen", "🌧️"),
    66: ("Gefr. Regen", "🌧️"), 67: ("Gefr. Regen", "🌧️"),
    71: ("Leichter Schnee", "🌨️"), 73: ("Schnee", "🌨️"), 75: ("Starker Schnee", "❄️"), 77: ("Schneegriesel", "🌨️"),
    80: ("Schauer", "🌦️"), 81: ("Schauer", "🌧️"), 82: ("Starke Schauer", "⛈️"),
    85: ("Schneeschauer", "🌨️"), 86: ("Schneeschauer", "❄️"),
    95: ("Gewitter", "⛈️"), 96: ("Gewitter + Hagel", "⛈️"), 99: ("Schweres Gewitter", "⛈️"),
}


def _cfg():
    try:
        return json.loads(_CFG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_text(url, timeout=8):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _get_json(url, timeout=8):
    return json.loads(_get_text(url, timeout))


def _wcode(c):
    return _WMO.get(int(c) if c is not None else -1, ("—", "•"))


def weather():
    cfg = _cfg()
    lat = cfg.get("lat", 52.52); lon = cfg.get("lon", 13.405); city = cfg.get("city", "—")
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
           "&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto&forecast_days=4"
           % (lat, lon))
    d = _get_json(url)
    cur = d.get("current", {}) or {}
    dl = d.get("daily", {}) or {}
    codes = dl.get("weather_code", []) or []
    tmax = dl.get("temperature_2m_max", []) or []
    tmin = dl.get("temperature_2m_min", []) or []
    dates = dl.get("time", []) or []
    days = []
    for i in range(min(4, len(codes))):
        lbl, ic = _wcode(codes[i])
        days.append({"date": dates[i] if i < len(dates) else "", "label": lbl, "icon": ic,
                     "max": tmax[i] if i < len(tmax) else None, "min": tmin[i] if i < len(tmin) else None})
    lbl, ic = _wcode(cur.get("weather_code"))
    return {"city": city, "lat": lat, "lon": lon, "temp": cur.get("temperature_2m"), "label": lbl, "icon": ic,
            "wind": cur.get("wind_speed_10m"), "humidity": cur.get("relative_humidity_2m"), "days": days}


def _clean(s):
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&#39;", "'").replace("&quot;", '"').strip())


def _img(block):
    """Bild-URL aus einem RSS-<item> (enclosure / media / <img> in description)."""
    for pat in (r'<enclosure[^>]+url="([^"]+)"[^>]*type="image',
                r'<media:content[^>]+url="([^"]+)"',
                r'<media:thumbnail[^>]+url="([^"]+)"',
                r'&lt;img[^&]*src=&quot;([^&]+)&quot;',
                r'<img[^>]+src="([^"]+)"'):
        m = re.search(pat, block, re.I | re.S)
        if m:
            return m.group(1).replace("&amp;", "&").strip()
    return ""


# Lokales Ortsverzeichnis: Ortsname im Schlagzeilen-Text -> Koordinaten (sofort, ohne Geocoder).
# Fokus Osthessen / Landkreis Fulda + große deutsche Städte (für überregionale Meldungen).
_GAZ = {
    "bad salzschlirf": (50.6244, 9.5064), "bad hersfeld": (50.8686, 9.7061),
    "poppenhausen": (50.5012, 9.8892), "großenlüder": (50.5906, 9.5397),
    "wasserkuppe": (50.4981, 9.9403), "eichenzell": (50.4783, 9.6900),
    "petersberg": (50.5767, 9.7375), "hosenfeld": (50.4989, 9.4739),
    "ebersburg": (50.4497, 9.7906), "burghaun": (50.7050, 9.7003),
    "künzell": (50.5486, 9.7286), "hünfeld": (50.6739, 9.7636),
    "gersfeld": (50.4494, 9.9256), "dipperz": (50.5439, 9.8067),
    "rasdorf": (50.7008, 9.8919), "nüsttal": (50.6664, 9.8256),
    "flieden": (50.4197, 9.5678), "lauterbach": (50.6383, 9.3958),
    "alsfeld": (50.7522, 9.2711), "kalbach": (50.3606, 9.6100),
    "hilders": (50.5722, 9.9497), "schlitz": (50.6714, 9.5586),
    "hersfeld": (50.8686, 9.7061), "neuhof": (50.4547, 9.6178),
    "vogelsberg": (50.5300, 9.2800), "fulda": (50.5528, 9.6808),
    "tann": (50.6408, 10.0186), "rhön": (50.4500, 9.9300),
    "berlin": (52.5200, 13.4050), "hamburg": (53.5500, 9.9930), "münchen": (48.1370, 11.5750),
    "köln": (50.9370, 6.9600), "frankfurt": (50.1100, 8.6820), "stuttgart": (48.7750, 9.1820),
    "düsseldorf": (51.2270, 6.7730), "leipzig": (51.3390, 12.3770), "dresden": (51.0500, 13.7370),
    "hannover": (52.3750, 9.7320), "bremen": (53.0790, 8.8010), "kassel": (51.3120, 9.4800),
    "wiesbaden": (50.0820, 8.2400), "erfurt": (50.9840, 11.0290), "magdeburg": (52.1200, 11.6270),
    "nürnberg": (49.4520, 11.0770), "dortmund": (51.5140, 7.4660), "mainz": (49.9920, 8.2470),
    "sachsen-anhalt": (51.9500, 11.6900), "hessen": (50.6500, 9.1600), "bayern": (48.7900, 11.5000),
}
_GAZ_KEYS = sorted(_GAZ.keys(), key=len, reverse=True)   # längste zuerst (bad hersfeld vor hersfeld)


def _locate(title):
    low = " " + title.lower() + " "
    for k in _GAZ_KEYS:
        if re.search(r"(?<![\wäöüß])" + re.escape(k) + r"(?![\wäöüß])", low):
            lat, lon = _GAZ[k]
            return {"place": k.title(), "lat": lat, "lon": lon}
    return None


def _feed_items(url, source, n):
    out = []
    try:
        raw = _get_text(url)
    except Exception:
        return out
    for m in re.finditer(r"<item>(.*?)</item>", raw, re.S):
        block = m.group(1)
        t = re.search(r"<title>(.*?)</title>", block, re.S)
        if not t:
            continue
        l = re.search(r"<link>(.*?)</link>", block, re.S)
        title = _clean(t.group(1))
        if not title:
            continue
        item = {"title": title, "link": (_clean(l.group(1)) if l else ""),
                "image": _img(block), "source": source}
        desc = re.search(r"<description>(.*?)</description>", block, re.S)
        haystack = title + " " + (_clean(desc.group(1))[:400] if desc else "")
        loc = _locate(haystack)
        if loc:
            item.update(loc)
        out.append(item)
        if len(out) >= n:
            break
    return out


def news(total=8):
    cfg = _cfg()
    feeds = cfg.get("news_feeds")
    if not feeds:
        feeds = [{"url": cfg.get("news_rss", "https://www.tagesschau.de/index~rss2.xml"), "source": "News"}]
    per = max(4, (total // max(1, len(feeds))) + 2)
    lists = [_feed_items(f.get("url", ""), f.get("source", "News"), per) for f in feeds]
    # round-robin merge, so every source shows near the top
    merged, i = [], 0
    while len(merged) < total and any(i < len(l) for l in lists):
        for l in lists:
            if i < len(l):
                merged.append(l[i])
                if len(merged) >= total:
                    break
        i += 1
    return merged
