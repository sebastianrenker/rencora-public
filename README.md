# 🟣 Rencora — Holographic AI Assistant

Ein JARVIS-artiger, sprachgesteuerter KI-Assistent mit **holografischen Oberflächen**,
**3D-Handsteuerung**, **Satellitenglobus**, **Info-Wall** und einem erweiterbaren Plugin-System.
Läuft headless im Hintergrund und bringt ein Web-Dashboard mit, das du vom PC, Handy oder
Beamer aus bedienst.

> **Rencora** ist eine umgebaute, stark erweiterte Abwandlung von **Mark LI / „JARVIS" von
> [FatihMakes](https://github.com/FatihMakes/Mark-LI)** und steht unter **CC BY-NC 4.0**
> (siehe [`NOTICE.md`](NOTICE.md) und [`LICENSE`](LICENSE)). Namensnennung ist erforderlich,
> kommerzielle Nutzung ist nicht gestattet.

---

## ✨ Features

- **Sprache** — Live-Sprachassistent (Google Gemini) mit Wakeword „Jarvis"/„Rencora" oder
  Dauer-Zuhören; optionaler Zweitanbieter **Grok/Groq** für schwere Aufgaben (spart Tokens).
- **Holo-Oberflächen** — Startzentrale, Tisch-/Leinwand-Projektion, 3D-Hologrammsteuerung per
  Webcam-Handtracking, kompaktes Panel, Fire-TV-HUD, Handy-Fernbedienung.
- **Info-Wall** — Wetter, Nachrichten (beliebige RSS-Quellen, mit Bildern & Kurz-Zusammenfassung),
  Satellitenkarte, Aufgaben, Krypto-Ticker.
- **3D-Globus** — Satellitenbild, Flug zu jedem Ort (Sprache/Suche), Wetter- & Wikipedia-Info,
  Nachrichten-Pins, ISS- & Flugverkehr-Layer, Ambient-Beamer-Modus.
- **Dokumente** — Fotos, PDFs, Word & Text lesen und laienverständlich erklären.
- **Mehr** — Morgenbriefing, Übersetzer, Kinomodus, Unwetter-Warnung, Gesichtserkennung,
  System-Status-Seite, Coding via Claude-Code-CLI, Smart-Home, Drucker, Timer/Wecker, „Brain"-Index.

## 🧩 Voraussetzungen

- **Python 3.11 / 3.12**
- **Google Gemini API-Key** (Pflicht, für Live-Voice): https://aistudio.google.com/apikey
- Optional: **ffmpeg** (Musik/Audio), **Groq**- oder **xAI-Grok**-Key (Zweitanbieter),
  **Cesium-ion-Token** (3D-Gelände), Webcam (Handtracking/Gesichtserkennung), Tailscale (Fernzugriff).

## 🚀 Installation

```bash
git clone https://github.com/<dein-name>/rencora.git
cd rencora
python -m venv .venv && .venv\Scripts\activate      # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

### Konfiguration (du richtest sie selbst ein)

Alle Vorlagen liegen in `config/` als `*.example.json`. Kopiere die, die du brauchst, und
entferne `.example` aus dem Namen:

```bash
# mindestens dein Gemini-Key:
copy config\api_keys.example.json config\api_keys.json     # macOS/Linux: cp
```

| Datei | Zweck |
|---|---|
| `config/api_keys.json` | **Gemini-API-Key** (Pflicht) |
| `config/owner.json` | Dein Name, GitHub-Handle, Assistentenname, Stimme, Sprache |
| `config/grok.json` | Optionaler Groq-/xAI-Key (Zweitanbieter) |
| `config/wall.json` | Ort (Wetter/Karte), Nachrichten-Feeds, Krypto-Coins |
| `config/github.json` | Dein GitHub-Name (oder in `owner.json` unter `github`) |
| `config/globe.json` | Optionaler Cesium-ion-Token (3D-Gelände) |
| `config/claude_code.json` | Ordner deiner Repos (Coding via Claude) |
| `config/voice.json` | Wakewords, Dauer-Zuhören, Vosk-Modellsprache |

> ⚠️ Deine echten `config/*.json` sind per `.gitignore` ausgeschlossen und werden **nie**
> committet. Nur die `*.example.json` liegen im Repo.

## ▶️ Starten

```bash
python run_headless.py            # headless (Dashboard auf http://localhost:8000)
# oder mit GUI:
python main.py
```

Dann im Browser **http://localhost:8000** öffnen — das ist die Startzentrale.

## 🗺️ Oberflächen

`/home` Startzentrale · `/wall` Info-Wall · `/globe` 3D-Globus · `/desk` Tisch ·
`/holo3d` 3D-Steuerung · `/holo` Panel · `/tv` Fire-TV · `/remote` Fernbedienung ·
`/brain` Wissens-Index · `/status` System-Status · `/settings` Einstellungen.

## 📜 Lizenz & Attribution

Dieses Projekt basiert auf **Mark LI / JARVIS von FatihMakes** und steht unter der
**Creative Commons BY-NC 4.0**. Das heißt: Namensnennung von FatihMakes erforderlich,
**keine kommerzielle Nutzung**. Details in [`NOTICE.md`](NOTICE.md) und [`LICENSE`](LICENSE).

Die Nutzung von Diensten Dritter (Gemini, Groq/xAI, YouTube via yt-dlp, OpenStreetMap,
Cesium, OpenSky u. a.) unterliegt deren jeweiligen Nutzungsbedingungen.
