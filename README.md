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

### Windows — easiest way (no command line needed)

1. Install **Python 3.12** from https://www.python.org/downloads/windows/ and tick
   **"Add python.exe to PATH"** in the installer.
2. Download Rencora: on this page click **Code → Download ZIP**, then unzip it
   (right-click → *Extract All*).
3. In the unzipped folder, double-click **`install.bat`** and wait until it says *Done*.
4. Double-click **`start.bat`**. The browser opens the setup page — paste your
   Gemini API key there. Done.

### Windows — with git (PowerShell)

```powershell
git clone https://github.com/sebastianrenker/rencora-public.git
cd rencora-public
.\install.bat
.\start.bat
```

<details>
<summary>Manual setup in PowerShell (without the scripts)</summary>

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_headless.py --local --open
```

Note: Windows PowerShell 5.1 does not support `&&` — run each line separately.
If you want to *activate* the venv and get an "execution of scripts is disabled"
error, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once (or just call
`.venv\Scripts\python.exe` directly as above — no activation needed).
</details>

### macOS / Linux

```bash
git clone https://github.com/sebastianrenker/rencora-public.git
cd rencora-public
bash install.sh
bash start.sh
```

Then open **http://127.0.0.1:8000/setup** and enter your Gemini API key.

### Configuration (optional, by hand)

The first start opens a setup page for your Gemini key. Everything else can be set
by copying a template from `config/` and dropping `.example` from the filename:

```powershell
# Windows (PowerShell)
Copy-Item config\api_keys.example.json config\api_keys.json
```

```bash
# macOS / Linux
cp config/api_keys.example.json config/api_keys.json
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

Use `start.bat` (Windows) or `bash start.sh` (macOS/Linux). Or by hand, from the
project folder:

```bash
.venv/Scripts/python run_headless.py --local --open   # Windows (macOS/Linux: .venv/bin/python)
# or with the desktop GUI:
.venv/Scripts/python main.py
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
