"""
Rencora background music — compiles music from YouTube by vibe/mood and plays it in
the background (audio only, no window, no ads, no YouTube opened).

How: yt-dlp searches YouTube and resolves the raw audio stream (which has no ad breaks —
those are injected by the YouTube player, not the stream); ffplay (-nodisp) plays it in
the background. A player thread keeps a queue and, radio-style, extends it with more of
the current mood so music never stops.

Note: streaming YouTube audio outside the YouTube player is against YouTube's Terms of
Service. This is provided for the owner's personal, private use only.

Engine: Mark-LI by FatihMakes (CC BY-NC 4.0) — see NOTICE.md.
"""
import os
import shutil
import subprocess
import threading
from collections import deque
import logging as _logging
_swallow_log = _logging.getLogger(__name__)

PLUGIN = {
    "name": "music",
    "description": (
        "Play/compile background music from YouTube by vibe or mood — audio only, no ads, "
        "runs in the background. Use for ANY music request. "
        "actions: 'play' (needs 'query' = mood/genre/artist/song, e.g. 'entspannte Lofi Beats', "
        "'Rockmusik zum Arbeiten', 'Hans Zimmer'), 'skip' (next track), 'stop', 'status' "
        "(what's playing), 'volume' (needs 'level' 0-100), 'video' (play a YouTube video/film "
        "fullscreen, needs 'query'), 'stop_video'. Use 'video' for 'spiel ein Video/Film', "
        "'zeig mir X auf YouTube'. "
        "Trigger: Musik, spiel/spiele, Lied, Song, Playlist, Radio, chillige/entspannte Musik, "
        "lauter/leiser (music), überspringen, weiter, Musik aus/stopp."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "play | skip | stop | status | volume"},
            "query": {"type": "STRING", "description": "Mood / genre / artist / song for action=play"},
            "level": {"type": "INTEGER", "description": "Volume 0-100 for action=volume"},
        },
        "required": ["action"],
    },
}


def _find_ffplay():
    p = shutil.which("ffplay")
    if p:
        return p
    # search common winget ffmpeg install locations
    for base in (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"),
                 r"C:\ffmpeg\bin", os.path.expandvars(r"%ProgramFiles%\ffmpeg\bin")):
        try:
            if os.path.isfile(os.path.join(base, "ffplay.exe")):
                return os.path.join(base, "ffplay.exe")
            for root, _dirs, files in os.walk(base):
                if "ffplay.exe" in files:
                    return os.path.join(root, "ffplay.exe")
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return None


class MusicPlayer:
    def __init__(self):
        self.queue = deque()
        self.lock = threading.Lock()
        self.proc = None
        self.thread = None
        self.running = False
        self.current_title = None
        self.mood = None
        self.volume = 70
        self.ffplay = _find_ffplay()

    # ---- yt-dlp helpers ----
    def _search(self, query, count):
        try:
            from yt_dlp import YoutubeDL
        except Exception:
            return None
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True,
                "noplaylist": True, "default_search": "ytsearch"}
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info("ytsearch%d:%s" % (count, query), download=False)
            out = []
            for e in (info.get("entries") or []):
                if e and e.get("id"):
                    out.append({"id": e["id"], "title": e.get("title", "Unbekannt")})
            return out
        except Exception:
            return []

    def _resolve(self, vid):
        try:
            from yt_dlp import YoutubeDL
        except Exception:
            return None
        opts = {"quiet": True, "no_warnings": True, "noplaylist": True,
                "format": "bestaudio/best"}
        try:
            with YoutubeDL(opts) as ydl:
                d = ydl.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
            return d.get("url")
        except Exception:
            return None

    # ---- playback thread ----
    def _loop(self):
        while self.running:
            with self.lock:
                item = self.queue.popleft() if self.queue else None
            if item is None:
                if self.mood:                              # radio: keep the vibe going
                    more = self._search(self.mood, 6) or []
                    with self.lock:
                        self.queue.extend(more)
                    if not self.queue:
                        break
                    continue
                break
            url = self._resolve(item["id"])
            if not url:
                continue
            if not self.running:
                break
            self.current_title = item["title"]
            try:
                self.proc = subprocess.Popen(
                    [self.ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet",
                     "-volume", str(self.volume), "-i", url],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=0x08000000)             # CREATE_NO_WINDOW
            except Exception:
                self.proc = None
                continue
            self.proc.wait()
            self.proc = None
        self.running = False
        self.current_title = None

    def _ensure_thread(self):
        if not (self.thread and self.thread.is_alive()):
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    # ---- public controls ----
    def play(self, query, count=8):
        if not self.ffplay:
            return "Ich finde ffplay nicht (Teil von ffmpeg) — Audio kann nicht abgespielt werden."
        entries = self._search(query, count)
        if entries is None:
            return "Fuer Musik fehlt yt-dlp (pip install yt-dlp)."
        if not entries:
            return "Ich habe zu '" + query + "' nichts gefunden."
        self.mood = query
        with self.lock:
            self.queue.extend(entries)
        self.running = True
        self._ensure_thread()
        return "Spiele jetzt Musik zu '" + query + "' im Hintergrund. Erster Titel: " + entries[0]["title"] + "."

    def skip(self):
        p = self.proc
        if p:
            try:
                p.terminate()
            except Exception:
                _swallow_log.debug("ignored error", exc_info=True)
            return "Ueberspringe zum naechsten Titel."
        return "Es laeuft gerade keine Musik."

    def stop(self):
        self.running = False
        with self.lock:
            self.queue.clear()
        p = self.proc
        if p:
            try:
                p.terminate()
            except Exception:
                _swallow_log.debug("ignored error", exc_info=True)
        self.current_title = None
        return "Musik gestoppt."

    def set_volume(self, level):
        try:
            self.volume = max(0, min(100, int(level)))
        except Exception:
            return "Bitte eine Lautstaerke zwischen 0 und 100 angeben."
        return "Lautstaerke auf " + str(self.volume) + "% — gilt ab dem naechsten Titel."

    def status(self):
        if self.current_title:
            return "Es laeuft gerade: " + self.current_title + " (Stimmung: " + str(self.mood or "?") + ")."
        if self.running:
            return "Musik wird vorbereitet…"
        return "Gerade laeuft keine Musik."

    def play_video(self, query, player=None):
        """Play a YouTube video (videos/trailers/films — not pirated content). On the Fire TV
        the /tv page embeds the YouTube player (handles DASH reliably). PC fallback: browser."""
        try:
            from yt_dlp import YoutubeDL
        except Exception:
            return "Fuer Videos fehlt yt-dlp (pip install yt-dlp)."
        vid, title = None, query
        try:
            with YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True,
                            "noplaylist": True, "default_search": "ytsearch"}) as ydl:
                info = ydl.extract_info("ytsearch1:" + query, download=False)
                e = (info.get("entries") or [None])[0]
                if e and e.get("id"):
                    vid = e["id"]; title = e.get("title", query)
        except Exception as ex:
            return "Video-Suche fehlgeschlagen: " + str(ex)
        if not vid:
            return "Ich habe zu '" + query + "' kein Video gefunden."
        # 1) Fire TV: send the video id -> /tv embeds the YouTube player
        tv = getattr(player, "tv_play", None) if player else None
        if tv:
            try:
                if tv(vid, title):
                    return "Spiele auf dem Fire TV: " + title + "."
            except Exception:
                _swallow_log.debug("ignored error", exc_info=True)
        # 2) PC fallback: open it in the browser
        try:
            import webbrowser
            webbrowser.open("https://www.youtube.com/watch?v=" + vid)
            return "Ich oeffne das Video auf dem PC: " + title + "."
        except Exception:
            return "Video gefunden (" + title + "), aber kein Fire TV verbunden."

    def stop_video(self):
        try:
            if getattr(self, "video_proc", None):
                self.video_proc.terminate()
                self.video_proc = None
                return "Video gestoppt."
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
        return "Es laeuft gerade kein Video."


_PLAYER = None
def _player():
    global _PLAYER
    if _PLAYER is None:
        _PLAYER = MusicPlayer()
    return _PLAYER


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "").strip().lower()
    mp = _player()
    try:
        if action == "play":
            out = mp.play((parameters.get("query") or "").strip() or "chillige Musik")
        elif action == "skip":
            out = mp.skip()
        elif action == "stop":
            out = mp.stop()
        elif action == "volume":
            out = mp.set_volume(parameters.get("level", 70))
        elif action == "status":
            out = mp.status()
        elif action == "video":
            out = mp.play_video((parameters.get("query") or "").strip() or "Musikvideo", player)
        elif action == "stop_video":
            out = mp.stop_video()
        else:
            out = "Unbekannte Musik-Aktion. Moeglich: play, skip, stop, status, volume, video, stop_video."
    except Exception as e:
        return "Die Musiksteuerung ist fehlgeschlagen: " + str(e)
    if player:
        try:
            player.write_log("JARVIS: " + out)
        except Exception:
            _swallow_log.debug("ignored error", exc_info=True)
    return out
