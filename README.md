# py-16

Eine Fantasy-Konsole im Stil der 16-Bit-Aera, geschrieben in Python mit Pygame.

## Eckdaten

| | py-16 |
|---|---|
| Aufloesung | 256 x 224 @ 60 FPS |
| Palette | 256 Farben (frei zuweisbar) |
| Sprite-Sheet | 256 x 256 (1024 Sprites a 8x8) |
| Sprite-Groessen | 8x8 bis 64x64 (`spr(id, x, y, w, h, flip_x, flip_y)`) |
| Map | 128 x 128 Tiles |
| Sound | 8 Kanaele, 4 Wellenformen (Square, Triangle, Saw, Noise) |
| Editoren | Sprite (F1), Map (F2) |
| Cart | JSON mit base64-Sheet (~140 KB) |

## Installation

```bash
pip install pygame numpy
```

(numpy ist optional, beschleunigt aber Bildladen und Cart-I/O deutlich)

## Installation

```bash
pip install pygame                      # Pflicht
pip install numpy pillow reportlab pypdf pymupdf   # Optional, fuer alle Features
```

Oder in einem Schritt mit den Optional-Gruppen:

```bash
pip install py-16[all]      # Alles
pip install py-16[fast]     # Nur numpy
pip install py-16[pdf]      # PDF-Export
pip install py-16[covers]   # PDF-Cover-Vorschauen
```

## Sicherheitshinweis

py-16 fuehrt den Code im Cart als ganz normalen Python-Code aus -
es gibt keine Sandbox. **Oeffne nur Carts, denen du vertraust.**

Ein boeser Cart kann alles, was Python kann: Dateien lesen/loeschen,
Internet-Verbindungen, dein Mikrofon, deine Webcam, dein Adressbuch.
Das gilt fuer .p16- und .pdf-Carts gleichermassen. Behandle Carts wie
Python-Skripte aus dem Internet, nicht wie Bilder oder Lieder.

Wenn du Carts aus dem Netz lädst, lies vorher den Code im Code-Editor
durch (F6 -> F8 zum Laden ohne Ausfuehrung -> dann kannst du den Code
sehen, bevor du F9 zum Reload druckst).

## Schnellstart

```python
import py16

def init():
    py16.sset(8, 0, 8)          # roter Pixel ins Sprite-Sheet
    py16.fset(1, 0, True)       # Sprite 1 bekommt Flag 0

def update():
    if py16.btn('right'):
        ...

def draw():
    py16.cls(0)
    py16.spr(1, 100, 50)
    py16.text("HELLO", 4, 4, 7)

py16.run(update, draw, init)
```

## Modulstruktur

```
py16/
├── __init__.py        Public-API (alles re-exportiert)
├── state.py           Zentraler mutabler Zustand
├── core.py            Konstanten, Palette, run(), Auto-Boot-Countdown
├── graphics.py        cls, pset, rect, line, text, camera, clip, pal/palt
├── sprites.py         spr, sset, sget, load_spritesheet
├── maps.py            mset, mget, draw_map, fset, fget
├── input.py           btn, btnp, mouse_*
├── audio.py           tone() + Wellenformen-Generator
├── sfx_data.py        Datenmodelle fuer SFX/Music
├── tracker.py         Hintergrund-Sequencer mit Effekten
├── mathx.py           rnd, flr, mid, sin, cos, atan2, t, fps
├── cart.py            save_cart, load_cart (.p16 und .pdf)
├── cart_pdf.py        PDF-Export mit Handbuch
├── cart_runtime.py    run_cart, push_cart, pop_cart (Stack)
├── config.py          ~/.py16/config.json verwalten
├── bios.py            BIOS-Bildschirm mit Cart-Liste, Power-Menue
├── editors.py         Sprite- und Map-Editor (F1/F2)
├── editors_audio.py   SFX- und Music-Editor (F3/F4)
└── code_editor.py     Code-Editor (F6) mit Live-Reload (F9)
```

## BIOS und Boot-Cart

py-16 startet wahlweise direkt in einen Cart oder in den BIOS-Bildschirm:

```bash
# Direkt einen Cart starten
python3 demo.py

# Mit Boot-Cart starten (laedt automatisch ~/.py16/carts/boot.p16,
# 3 Sekunden Countdown, ESC oder beliebige Taste = BIOS)
python3 -c "import py16; py16.run()"
```

Der BIOS-Bildschirm zeigt alle Carts im Cart-Verzeichnis und bietet:
- Cart starten (Enter)
- Code-Editor fuer neuen Cart (F6)
- Power-Menue mit Shutdown/Reboot/Quit (F12)

**F12** ist ueberall der Notausgang zurueck zum BIOS - egal ob ein
Cart abgestuerzt ist oder ein Editor offen ist.

### Cart-Verzeichnis

Default: `~/.py16/carts/`. Override per Umgebungsvariable
`PY16_CARTS_DIR=/pfad/zu/carts`.

Configuration in `~/.py16/config.json`:

```json
{
  "carts_dir":      "~/.py16/carts",
  "boot_cart":      "boot.p16",
  "power_off_cmd":  "sudo poweroff",
  "reboot_cmd":     "sudo reboot",
  "boot_countdown": 3
}
```

### Cart-Wechsel zur Laufzeit

```python
py16.run_cart("/pfad/spiel.p16")     # Reset, alter Cart wird verworfen
py16.push_cart("/pfad/menu.p16")     # Stack: vorigen Cart merken
py16.pop_cart()                       # zurueck zum vorherigen Cart
py16.go_to_bios()                     # zurueck ins BIOS
```

Der Boot-Cart-Pattern: ein Browser-Cart nutzt `push_cart()` zum Starten
eines Spiels; das Spiel nutzt `pop_cart()` oder F12 -> BIOS, um zurueck
zu kommen.

### Beispiel-Boot-Cart

`boot_cart.py` ist ein fertiger Cart-Browser im 2x3-Grid mit Cover-Stilen.
Speichern als `~/.py16/carts/boot.p16` und beim naechsten Start wird er
automatisch geladen.

### Pi-Image-Hinweise

Fuer eine Einplatinen-Konsole:
- System auf Auto-Login fuer den Pi-User konfigurieren
- `~/.bash_profile`: `python3 -c "import py16; py16.run()"`
- `power_off_cmd` muss ohne Passwort funktionieren -> `visudo`:
  `pi ALL=NOPASSWD: /sbin/poweroff, /sbin/reboot`
- Vollbild aktivieren in `~/.py16/config.json`: `"fullscreen": true`

### Vollbild

```python
py16.toggle_fullscreen()
```

Oder per Tastatur **F11** zur Laufzeit. Persistent ueber Config:

```json
{
  "fullscreen":     true,
  "display_scale":  "auto",        // oder fester Faktor wie 4
  "hide_cursor":    "auto"         // im Vollbild aus
}
```

Bei `display_scale: "auto"` waehlt py-16 den groessten ganzzahligen
Skalierungsfaktor, der auf den Bildschirm passt - ergibt scharfe Pixel
ohne Sub-Pixel-Filtering. Das nicht abgedeckte Letterbox-Gebiet wird
schwarz gefuellt. Maus-Koordinaten werden korrekt zurueckgerechnet.

### PDF-Cover-Vorschauen

`py16.get_cart_cover(pdf_path, w, h)` liefert ein 2D-Array mit
Paletten-Indizes als Vorschau der ersten PDF-Seite. Cache unter
`~/.py16/cart_covers/`. Der mitgelieferte `boot_cart.py` zeigt damit
echte Cover statt generischer Booklet-Symbole.

Braucht `pip install pymupdf pillow`.

## API-Uebersicht

### Grafik

| Funktion | Zweck |
|---|---|
| `cls(c=0)` | Bildschirm fuellen |
| `pset(x, y, c)` / `pget(x, y)` | Einzelnes Pixel |
| `rect(x, y, w, h, c)` / `rectfill(...)` | Rechteck |
| `line(x0, y0, x1, y1, c)` | Linie |
| `circ(x, y, r, c)` / `circfill(...)` | Kreis |
| `text(s, x, y, c=7)` | Text mit eingebautem 3x5-Font |
| `camera(x, y)` | Kamera-Offset setzen |
| `clip(x, y, w, h)` | Scissor-Rechteck |
| `pal(c0, c1)` | Farbe c0 wird als c1 dargestellt |
| `palt(c, transparent)` | Transparenz-Set anpassen |

### Sprites & Map

| Funktion | Zweck |
|---|---|
| `sset(x, y, c)` / `sget(x, y)` | Pixel im Sprite-Sheet |
| `spr(id, x, y, w=1, h=1, flip_x=False, flip_y=False)` | Sprite zeichnen |
| `load_spritesheet(file)` | PNG laden + auf Palette quantisieren |
| `mset(cx, cy, id)` / `mget(cx, cy)` | Map-Zelle |
| `draw_map(cx, cy, sx, sy, w, h, layer_flag=-1)` | Map-Bereich |
| `fset(id, flag, value)` / `fget(id, flag)` | Sprite-Flags 0..7 |

### Eingabe

| Funktion | Zweck |
|---|---|
| `btn(name)` | Taste gehalten? |
| `btnp(name)` | Taste in diesem Frame neu gedrueckt? |
| `mouse_x()`, `mouse_y()` | Mausposition (Logik-Koordinaten) |
| `mouse_btn(idx)`, `mouse_btnp(idx)` | Maustasten 0/1/2 |

Tasten: `up`, `down`, `left`, `right`, `z`, `x`, `a`, `s`, `space`, `enter`, `shift`

### Audio

| Funktion | Zweck |
|---|---|
| `sfx(id, channel=-1)` | SFX-Patch abspielen |
| `music(track_id, fade_ms=0)` | Music-Track im Hintergrund starten (-1 = Stop) |
| `tone(pitch_hz, dur_ms, wave, channel=-1)` | Low-Level-Ton ohne Patch |

Wellenformen: `WAVE_SQUARE`, `WAVE_TRIANGLE`, `WAVE_SAW`, `WAVE_NOISE`

**SFX-Patches (64 Slots):** Jeder Patch hat 32 Notenzellen mit Note,
Instrument (8 Wellenformen-Varianten), Lautstaerke und Effekt
(Slide, Vibrato, Drop, Fade-In/Out, Arpeggio fast/slow).

**Music-Patterns (64 Slots):** Jedes Pattern kombiniert 4 SFX-IDs
fuer 4 parallele Kanaele.

**Music-Tracks (8 Slots):** Eine Sequenz von Pattern-IDs, die nacheinander
gespielt werden und am Ende loopen.

### Editoren (zur Laufzeit)

| Taste | Wirkung |
|---|---|
| F1 | Sprite-Editor toggeln |
| F2 | Map-Editor toggeln |
| F3 | SFX-Editor toggeln |
| F4 | Music-Editor toggeln |
| F6 | Code-Editor toggeln |
| F9 | Code-Reload (im Editor: Code ausfuehren) |
| F5 | Cart speichern (`cart.p16` oder `.pdf`) |
| F8 | Cart laden |
| ESC | Editor verlassen / Spiel beenden |

**Code-Editor:** Vollstaendiger Texteditor mit Cursor, Selection,
Copy/Cut/Paste (Ctrl+C/X/V), Undo/Redo (Ctrl+Z/Y), Suche (Ctrl+F),
Auto-Indent, Tab/Shift-Tab. Speichert mit Ctrl+S in die externe
`.py`-Datei. Mit F9 wird der Code zur Laufzeit neu kompiliert und
`update`/`draw` ersetzt - kein Programmneustart noetig.

### PDF-Cart-Export

Carts koennen als PDF mit Handbuch und eingebettetem Cart exportiert
werden:

```python
py16.export_pdf("game.pdf", title="MY GAME", author="ME")
# oder einfach:
py16.save_cart("game.pdf")
```

Das PDF enthaelt:
- **Cover-Seite** im Box-Stil mit Sprite-Vorschau
- **Manual-Seite** aus `# @manual ... # @end`-Kommentaren im Code
- **Asset-Seite** mit Sprite-Sheet, Map, SFX-Liste, Tracks
- **Code-Listing** im 80er-Stil mit Zeilennummern
- **Cart-Anhang** (`.p16`-Datei) als PDF-Attachment

Laden geht ueber `py16.load_cart("game.pdf")` - der Cart-Anhang wird
automatisch extrahiert.

Manual-Format im Code:

```python
# @manual
# @description
# Beschreibung des Spiels.
#
# @controls
# Pfeile : Bewegen
# Z      : Springen
#
# @credits
# Autor: Du
# @end
```

PDF-Export braucht: `pip install reportlab pypdf pillow`

**SFX-Editor:** Tracker-Raster mit 32 Notenzellen. Maus klickt Zellen an,
Pfeiltasten navigieren, +/- aendert Werte. Klavier-Tasten (Z-X-C... fuer
Oktave 3, Q-W-E... fuer Oktave 4) testen Tonhoehen live UND schreiben sie
in die aktuelle Zelle. SPACE spielt den ganzen Patch ab.

**Music-Editor:** Track-Sequenz oben (16 Pattern-Slots), Pattern-Editor
darunter (4 Kanaele mit SFX-IDs). TAB wechselt Fokus, A/S waehlt Track,
,/. waehlt Pattern. SPACE spielt Track, ENTER spielt nur Pattern.

## Lizenz

GPLv3. Siehe LICENSE-Datei für weitere Details.
