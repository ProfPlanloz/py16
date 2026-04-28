# Changelog

Alle nennenswerten Änderungen an py-16 werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
und das Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [1.0.0] - 2026-04-28

Erste öffentliche Veröffentlichung.

### Hinzugefügt

- Engine mit 256×224 Auflösung @ 60 FPS
- 256-Farben-Palette, frei zuweisbar
- Sprite-Sheet 256×256 (1024 Sprites à 8×8), Multi-Cel-Sprites mit Flip
- Map 128×128 Tiles mit Multi-Layer-Rendering über Sprite-Flags
- Audio-System mit 8 Kanälen und 4 Wellenformen
  (Square, Triangle, Saw, Noise)
- SFX-Patches mit Tracker-Effekten: Slide, Vibrato, Drop, Fade-In/Out,
  Arpeggio fast/slow
- Music-Tracks aus Pattern-Sequenzen, läuft im Hintergrund
- Eingebauter Sprite-Editor (F1) mit Maus-Pixel-Painter
- Map-Editor (F2) mit scrollbarer Map-Ansicht und Tile-Picker
- SFX-Editor (F3) mit Tracker-Raster und Klavier-Tastatur
- Music-Editor (F4) für Pattern- und Track-Komposition
- Code-Editor (F6) mit Cursor, Selection, Clipboard, Undo/Redo, Suche,
  Auto-Indent
- Live-Reload (F9) für Cart-Code ohne Programmneustart
- Cart-Format `.p16` (JSON mit base64-Sheet)
- Cart-Format `.pdf` mit Cover, Handbuch, Asset-Übersicht und
  Code-Listing - Spielcart und Handbuch in einer Datei
- Manual-Sektionen aus `# @manual ... # @end`-Kommentaren extrahiert
- BIOS-Bildschirm mit Cart-Liste, Power-Menü, Config-Verwaltung
- Auto-Boot-Cart mit Countdown
- Cart-Stack (`run_cart`, `push_cart`, `pop_cart`) für Cart-Wechsel
  zur Laufzeit
- PDF-Cover-Vorschauen im Boot-Cart-Browser (mit Cache)
- Vollbild-Modus (F11), automatische Skalierung mit Letterboxing
- Linux-Power-Befehle (poweroff/reboot) konfigurierbar
- Beispiel-Boot-Cart mit Cover-Browser im 2×3-Grid
- Demo-Cart mit Plattformer, Parallax, Multi-Layer-Map, Sound-Demos

### Bekannte Einschränkungen

- Cart-Code läuft ohne Sandbox - nur vertrauenswürdige Carts laden
- Audio-Effekte werden tickweise simuliert, nicht streaming-glatt
  (16-Bit-Charakter)
- Code-Editor zeigt Lowercase-Buchstaben als Großbuchstaben (Originalfall
  bleibt im Speicher erhalten)
