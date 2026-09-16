# 🟣 Rencora — Holographic AI Assistant

A JARVIS-style, voice-driven AI assistant with **holographic surfaces**,
**3D hand control**, a **satellite globe**, an **info wall**, and an extensible
plugin system. It runs headless in the background and ships a web dashboard you
drive from a PC, phone, or projector.

> **Rencora** is a heavily rebuilt and extended derivative of **Mark LI / "JARVIS"
> by [FatihMakes](https://github.com/FatihMakes/Mark-LI)**, licensed under
> **CC BY-NC 4.0** (see [`NOTICE.md`](NOTICE.md) and [`LICENSE`](LICENSE)).
> Attribution is required; commercial use is not permitted.

---

## ✨ Features

- **Voice** — live voice assistant (Google Gemini) with the wake word "Jarvis"/"Rencora"
  or continuous listening; optional secondary provider **Grok/Groq** for heavy tasks
  (saves tokens).
- **Holographic surfaces** — home hub, table/screen projection, 3D hologram control via
  webcam hand tracking, a compact panel, a Fire TV HUD, and a phone remote.
- **Info wall** — weather, news (any RSS source, with images and short summaries),
  satellite map, tasks, crypto ticker.
- **3D globe** — satellite imagery, fly to any location (voice/search), weather and
  Wikipedia info, news pins, ISS and air-traffic layers, ambient projector mode.
- **Documents** — read photos, PDFs, Word, and text and explain them in plain language.
- **More** — morning briefing, translator, cinema mode, severe-weather alerts, face
  recognition, system status page, coding via the Claude Code CLI, smart home, printer,
  timers/alarms, a "brain" knowledge index.

## 🧩 Requirements

- **Python 3.11 / 3.12**
- **Google Gemini API key** (required, for live voice): https://aistudio.google.com/apikey
- Optional: **ffmpeg** (music/audio), a **Groq** or **xAI Grok** key (secondary provider),
  a **Cesium ion token** (3D terrain), a webcam (hand tracking/face recognition),
  Tailscale (remote access).

## 🚀 Installation

```bash
git clone https://github.com/<your-name>/rencora.git
cd rencora
python -m venv .venv && .venv\Scripts\activate      # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

### Configuration (you set it up yourself)

All templates live in `config/` as `*.example.json`. Copy the ones you need and
drop `.example` from the filename:

```bash
# at minimum your Gemini key:
copy config\api_keys.example.json config\api_keys.json     # macOS/Linux: cp
```

| File | Purpose |
|---|---|
| `config/api_keys.json` | **Gemini API key** (required) |
| `config/owner.json` | Your name, GitHub handle, assistant name, voice, language |
| `config/grok.json` | Optional Groq/xAI key (secondary provider) |
| `config/wall.json` | Location (weather/map), news feeds, crypto coins |
| `config/github.json` | Your GitHub name (or in `owner.json` under `github`) |
| `config/globe.json` | Optional Cesium ion token (3D terrain) |
| `config/claude_code.json` | Folder of your repos (coding via Claude) |
| `config/voice.json` | Wake words, continuous listening, Vosk model language |

> ⚠️ Your real `config/*.json` files are excluded via `.gitignore` and are **never**
> committed. Only the `*.example.json` templates live in the repo.

## ▶️ Running

```bash
python run_headless.py            # headless (dashboard on http://localhost:8000)
# or with GUI:
python main.py
```

Then open **http://localhost:8000** in the browser — that is the home hub.

## 🗺️ Surfaces

`/home` home hub · `/wall` info wall · `/globe` 3D globe · `/desk` table ·
`/holo3d` 3D control · `/holo` panel · `/tv` Fire TV · `/remote` remote ·
`/brain` knowledge index · `/status` system status · `/settings` settings.

## 📜 License & attribution

This project is based on **Mark LI / JARVIS by FatihMakes** and is licensed under
**Creative Commons BY-NC 4.0**: attribution to FatihMakes is required, and
**no commercial use** is allowed. Details in [`NOTICE.md`](NOTICE.md) and
[`LICENSE`](LICENSE).

Use of third-party services (Gemini, Groq/xAI, YouTube via yt-dlp, OpenStreetMap,
Cesium, OpenSky, and others) is subject to their respective terms of service.
