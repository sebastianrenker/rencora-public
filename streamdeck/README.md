# 🎛️ Rencora × Stream Deck

30 Rencora-Funktionen für dein Stream Deck (2 Seiten à 5×3). Jeder Knopf löst **still**
(ohne Fenster) eine Rencora-Aktion aus — Sprach-/Assistenten-Aktionen beantwortet Rencora
mit ihrer Stimme.

## Einrichten (einmalig)
1. **Rencora muss laufen** (`Rencora.exe`) — das Dashboard liegt auf `http://localhost:8000`.
   Nach dem Einbau der Stream-Deck-Funktion **einmal neu starten**.
2. Im **Stream-Deck-Programm** pro Taste die Aktion **„System → Öffnen"** (System > Open) wählen
   und die passende **`.vbs`** aus diesem Ordner (`streamdeck\`) auswählen.
3. Titel + Symbol (Emoji) laut Plan setzen. Fertig — die `.vbs` löst geräuschlos aus.

> Alles läuft nur lokal (localhost, kein Token). Nichts verlässt deinen PC.

## Seite 1 — Steuerung & Alltag
| | | | | |
|---|---|---|---|---|
| 🎙️ Wecken<br>`p1_01_wake` | 👂 Dauer-Zuhören<br>`p1_02_continuous_on` | 🔇 Nur Wakeword<br>`p1_03_continuous_off` | 🎵 Musik<br>`p1_04_music_play` | ⏭️ Nächster<br>`p1_05_music_skip` |
| ⏹️ Stopp<br>`p1_06_music_stop` | 🔊 Lauter<br>`p1_07_music_vol_up` | 🔉 Leiser<br>`p1_08_music_vol_down` | 🌤️ Wetter<br>`p1_09_weather` | 📰 Nachrichten<br>`p1_10_news` |
| ☀️ Morgenbriefing<br>`p1_11_morning` | 👁️ Was siehst du<br>`p1_12_look` | 📲 WhatsApp<br>`p1_13_whatsapp` | 🈺 Übersetzer EN<br>`p1_14_translate_en` | 📝 Meine Liste<br>`p1_15_tasks` |

## Seite 2 — Flächen & Extras
| | | | | |
|---|---|---|---|---|
| 🏠 Start<br>`p2_01_open_home` | 🌐 Info-Wall<br>`p2_02_open_wall` | 🛰️ Globus<br>`p2_03_open_globe` | 🔬 Objekt-Labor<br>`p2_04_open_lab` | 🧊 3D-Steuerung<br>`p2_05_open_3d` |
| 🖐️ Tisch<br>`p2_06_open_desk` | 📺 Leinwand<br>`p2_07_open_stage` | 📡 Fire-TV<br>`p2_08_open_tv` | 🧠 Brain<br>`p2_09_open_brain` | 📊 Status<br>`p2_10_open_status` |
| 🌍 Globus-Beamer<br>`p2_11_open_ambient` | 📄 Dokument erklären<br>`p2_12_advisor` | 🎬 Kinomodus an<br>`p2_13_kino_on` | 💡 Kinomodus aus<br>`p2_14_kino_off` | ⛈️ Unwetter-Check<br>`p2_15_weatheralert` |

## Was die Knöpfe tun
- **Steuerung**: Wecken, Wakeword-/Dauer-Modus, Musik (an/nächster/stopp/lauter/leiser).
- **Sprache**: Wetter, Nachrichten-Überblick, Morgenbriefing, „Was siehst du", WhatsApp vorlesen,
  Übersetzer-Modus, Aufgabenliste, Unwetter-Check — Rencora antwortet mit ihrer Stimme.
- **Flächen** (öffnen als App-Fenster): Start, Info-Wall, Globus (+ Beamer-Modus), Objekt-Labor,
  3D, Tisch, Leinwand, Fire-TV, Brain, Status.
- **Szenen**: Kinomodus an/aus, Dokument erklären.

## Eigene Knöpfe
Beliebigen Sprachbefehl als Knopf: eine `.vbs` mit
`h.Open "GET", "http://localhost:8000/api/sd?say=DEIN%20BEFEHL", False` — Rencora führt ihn aus.
