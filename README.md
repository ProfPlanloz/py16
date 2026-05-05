# py-16

A 16-bit-era fantasy console written in Python with Pygame.

## Specs

| | py-16 |
|---|---|
| Resolution | 256 x 224 @ 60 FPS |
| Palette | 256 colors (freely assignable) |
| Sprite sheet | 256 x 256 (1024 sprites of 8x8) |
| Sprite sizes | 8x8 to 64x64 (`spr(id, x, y, w, h, flip_x, flip_y)`) |
| Map | 128 x 128 tiles |
| Sound | 8 channels, 4 waveforms (Square, Triangle, Saw, Noise) with ADSR + PWM |
| Editors | Sprite (F1), Map (F2), SFX (F3), Music (F4), Code (F6), PDF (F7) |
| Cart | JSON with base64 sheet (~140 KB) - or as PDF with manual |

## Installation

```bash
pip install pygame                                 # required
pip install numpy pillow reportlab pypdf pymupdf   # optional, for all features
```

Or in one step using the optional groups:

```bash
pip install py-16[all]      # everything
pip install py-16[fast]     # numpy only
pip install py-16[pdf]      # PDF export
pip install py-16[covers]   # PDF cover previews
```

## Security warning

py-16 runs cart code as plain Python - **there is no sandbox**.
Only open carts you trust.

A malicious cart can do anything Python can: read or delete files,
make network connections, access your microphone, webcam, address
book. This applies to both `.p16` and `.pdf` carts. Treat carts
like Python scripts from the internet, not like images or songs.

If you load carts from the net, read the code in the code editor
first (F6 -> F8 to load without execution -> review the code before
pressing F9 to reload).

## Quick start

```python
import py16

def init():
    py16.sset(8, 0, 8)          # red pixel into sprite sheet
    py16.fset(1, 0, True)       # sprite 1 gets flag 0

def update():
    if py16.btn('right'):
        ...

def draw():
    py16.cls(0)
    py16.spr(1, 100, 50)
    py16.text("HELLO", 4, 4, 7)

py16.run(update, draw, init)
```

## Module structure

```
py16/
├── __init__.py        Public API (everything re-exported)
├── state.py           Central mutable state
├── core.py            Constants, palette, run(), auto-boot countdown
├── graphics.py        cls, pset, rect, line, text, camera, clip, pal/palt
├── sprites.py         spr, sset, sget, load_spritesheet
├── maps.py            mset, mget, draw_map, fset, fget
├── input.py           btn, btnp, mouse_*
├── audio.py           tone() + waveform generator with ADSR/PWM
├── sfx_data.py        Data models for SFX/music
├── tracker.py         Background sequencer with effects
├── mathx.py           rnd, flr, mid, sin, cos, atan2, t, fps
├── cart.py            save_cart, load_cart (.p16 and .pdf)
├── cart_pdf.py        PDF export with manual
├── cart_runtime.py    run_cart, push_cart, pop_cart (stack)
├── config.py          ~/.py16/config.json management
├── bios.py            BIOS screen with cart list, power menu
├── editors.py         Sprite + map editor (F1/F2)
├── editors_audio.py   SFX + music editor (F3/F4)
├── editor_pdf.py      PDF metadata editor (F7)
└── code_editor.py     Code editor (F6) with live reload (F9)
```

## BIOS and boot cart

py-16 either starts directly into a cart, or into the BIOS screen:

```bash
# Start a cart directly
python3 demo.py

# Start with auto-boot (loads ~/.py16/carts/boot.p16 automatically,
# 3-second countdown, ESC or any key cancels into BIOS)
python3 -c "import py16; py16.run()"
```

The BIOS screen shows all carts in the cart directory and offers:
- Start cart (Enter)
- Code editor for new cart (F6)
- Power menu with shutdown/reboot/quit (F12)

**F12** is the universal escape hatch back to the BIOS - no matter
whether a cart crashed or an editor is open.

### Cart directory

Default: `~/.py16/carts/`. Override via environment variable
`PY16_CARTS_DIR=/path/to/carts`.

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

### Cart switching at runtime

```python
py16.run_cart("/path/game.p16")     # reset, old cart discarded
py16.push_cart("/path/menu.p16")    # stack: remember previous cart
py16.pop_cart()                      # back to previous cart
py16.go_to_bios()                    # back to BIOS
```

The boot-cart pattern: a browser cart uses `push_cart()` to start a
game; the game uses `pop_cart()` (or the player presses F12 -> BIOS)
to come back.

### Example boot cart

`boot_cart.py` is a ready-made cart browser as a 2x3 grid with cover
styles. Save it as `~/.py16/carts/boot.p16` and it will load
automatically next time.

### Pi/SBC setup

For a single-board console:
- Configure auto-login for the pi user
- `~/.bash_profile`: `python3 -c "import py16; py16.run()"`
- `power_off_cmd` must work without password -> `visudo`:
  `pi ALL=NOPASSWD: /sbin/poweroff, /sbin/reboot`
- Activate fullscreen in `~/.py16/config.json`: `"fullscreen": true`

### Fullscreen

```python
py16.toggle_fullscreen()
```

Or press **F11** at runtime. Persistent via config:

```json
{
  "fullscreen":     true,
  "display_scale":  "auto",        // or fixed factor like 4
  "hide_cursor":    "auto"         // off in fullscreen
}
```

With `display_scale: "auto"` py-16 picks the largest integer scale
factor that fits the screen - producing crisp pixels with no
sub-pixel filtering. Letterbox areas are filled black. Mouse
coordinates are correctly back-projected.

### PDF cover previews

`py16.get_cart_cover(pdf_path, w, h)` returns a 2D array of palette
indices as a preview of the first PDF page. Cached under
`~/.py16/cart_covers/`. The bundled `boot_cart.py` uses this to show
real covers instead of generic booklet icons.

Needs `pip install pymupdf pillow`.

## API overview

### Graphics

| Function | Purpose |
|---|---|
| `cls(c=0)` | Clear screen |
| `pset(x, y, c)` / `pget(x, y)` | Single pixel |
| `rect(x, y, w, h, c)` / `rectfill(...)` | Rectangle |
| `line(x0, y0, x1, y1, c)` | Line |
| `circ(x, y, r, c)` / `circfill(...)` | Circle |
| `text(s, x, y, c=7)` | Text in built-in 3x5 font |
| `camera(x, y)` | Set camera offset |
| `clip(x, y, w, h)` | Scissor rect |
| `pal(c0, c1)` | Color c0 displays as c1 |
| `palt(c, transparent)` | Adjust transparency set |

### Sprites & map

| Function | Purpose |
|---|---|
| `sset(x, y, c)` / `sget(x, y)` | Pixel in sprite sheet |
| `spr(id, x, y, w=1, h=1, flip_x=False, flip_y=False)` | Draw sprite |
| `load_spritesheet(file)` | Load PNG + quantize to palette |
| `mset(cx, cy, id)` / `mget(cx, cy)` | Map cell |
| `draw_map(cx, cy, sx, sy, w, h, layer_flag=-1)` | Draw map region |
| `fset(id, flag, value)` / `fget(id, flag)` | Sprite flags 0..7 |

### Input

| Function | Purpose |
|---|---|
| `btn(name)` | Held this frame? |
| `btnp(name)` | Just pressed this frame? |
| `mouse_x()`, `mouse_y()` | Mouse position (logic coords) |
| `mouse_btn(idx)`, `mouse_btnp(idx)` | Mouse buttons 0/1/2 |

Keys: `up`, `down`, `left`, `right`, `z`, `x`, `a`, `s`, `space`, `enter`, `shift`

### Audio

| Function | Purpose |
|---|---|
| `sfx(id, channel=-1)` | Play SFX patch |
| `music(track_id, fade_ms=0)` | Start music track in background (-1 = stop) |
| `tone(pitch_hz, dur_ms, wave, ...)` | Low-level tone without patch |

Waveforms: `WAVE_SQUARE`, `WAVE_TRIANGLE`, `WAVE_SAW`, `WAVE_NOISE`

**SFX patches (64 slots):** Each patch has 32 note cells with note,
instrument (8 waveform variants), volume and effect (slide, vibrato,
drop, fade in/out, arpeggio fast/slow). Plus per-patch ADSR envelope
and pulse-width modulation.

**Music patterns (64 slots):** Each pattern combines 4 SFX IDs for
4 parallel channels.

**Music tracks (8 slots):** A sequence of pattern IDs that play in
order and loop at the end.

### Audio synthesis (ADSR + PWM)

py-16 has a 16-bit audio engine with 8 channels, 4 waveforms, and
per-SFX-patch ADSR envelope plus pulse-width modulation:

```python
py16.tone(440, duration_ms=200, wave=py16.WAVE_SQUARE,
          attack_ms=20, decay_ms=50, sustain=0.6, release_ms=100,
          pulse_width=0.25)
```

In the SFX editor (F3), **E** toggles envelope-edit mode. Use up/down
arrows to switch between ATK / DEC / SUS / REL / PW, left/right
arrows to adjust the value. A live curve shows how the sound evolves.

ADSR and pulse-width are stored per SFX patch and restored when the
cart loads. Old carts without these fields load with default values
(flat envelope, 50% square wave).

### Editors at runtime

| Key | Effect |
|---|---|
| F1 | Toggle sprite editor |
| F2 | Toggle map editor |
| F3 | Toggle SFX editor |
| F4 | Toggle music editor |
| F6 | Toggle code editor |
| F7 | Toggle PDF editor (cover/title/author before PDF export) |
| F9 | Reload cart code (in editor: run code) |
| F11 | Toggle fullscreen |
| F12 | Back to BIOS (universal escape) |
| F5 | Save cart (`.p16` AND `.pdf` in parallel) |
| F8 | Load cart (prefers `.pdf`, falls back to `.p16`) |
| ESC | Leave editor / quit game |

**Code editor:** Full-featured text editor with cursor, selection,
copy/cut/paste (Ctrl+C/X/V), undo/redo (Ctrl+Z/Y), search (Ctrl+F),
auto-indent, Tab/Shift-Tab. Ctrl+S writes to the external `.py` file.
F9 recompiles cart code at runtime and replaces `update`/`draw` -
no program restart needed.

**PDF editor (F7):** Live preview of the cover page with editable
metadata. Edit title, author, cover style, four cover colors and font
before saving as PDF. Three tabs:

- **META** - title, author, cover style (sheet/map/screenshot/custom)
- **STYLE** - 4 colors (background, title band, title text, author
  text) + font (helvetica/courier/times/pixel)
- **IMAGE** - load custom PNG/JPG to embed as cover (max 200KB)

Ctrl+S saves both `.p16` and `.pdf` with the new metadata. Values
persist in the cart (`meta` field), so they're restored next time.
The `@manual` block from the code is shown live (read-only - edit it
in the code editor).

### Save and load

**Save (F5):** saves the current cart next to the running file - if
you start `python3 demo.py` and press F5, you get `demo.p16` and
`demo.pdf` right next to your `demo.py`. If no source path is known
(e.g. new cart from BIOS), the cart lands as
`untitled.p16`/`untitled.pdf` in the configured cart directory
(default `~/.py16/carts/`).

**Load (F8):** prefers `.pdf` (if present), falls back to `.p16`.
This makes the PDF the canonical form, always containing your latest
state - including the manual.

### PDF cart export

Carts can be exported as PDF with manual and embedded cart:

```python
py16.export_pdf("game.pdf", title="MY GAME", author="ME")
# or just:
py16.save_cart("game.pdf")
```

The PDF contains:
- **Cover page** in box style with sprite preview
- **Manual page** from `# @manual ... # @end` comments in code
- **Asset page** with sprite sheet, map, SFX list, tracks
- **Code listing** in 80s style with line numbers
- **Cart attachment** (`.p16` file) as PDF attachment

Loading via `py16.load_cart("game.pdf")` automatically extracts the
cart attachment.

Manual format in code:

```python
# @manual
# @description
# Description of the game.
#
# @controls
# Arrows : Move
# Z      : Jump
#
# @credits
# Author: You
# @end
```

PDF export needs: `pip install reportlab pypdf pillow`

**SFX editor:** Tracker grid with 32 note cells. Click cells with the
mouse, navigate with arrow keys, +/- changes values. Piano keys
(Z-X-C... for octave 3, Q-W-E... for octave 4) test pitches live AND
write them into the current cell. SPACE plays the whole patch.

**Music editor:** Track sequence at top (16 pattern slots), pattern
editor below (4 channels with SFX IDs). TAB cycles focus, A/S
selects track, ,/. selects pattern. SPACE plays track, ENTER plays
pattern only.

## License

GNU General Public License v3 (GPLv3)
