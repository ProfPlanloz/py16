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
├── tracker.py         background sequencer with effects
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

The cover cache grows over time, especially if you delete or rename
cart files. Clean it up with:

```bash
py16 --cache-stats           # show what's cached
py16 --cleanup-cache         # remove orphans (default)
py16 --cleanup-cache --age 30          # also remove entries older than 30 days
py16 --cleanup-cache --size 50         # keep total size below 50 MB
py16 --cleanup-cache --dry-run         # show what would be removed
```

There's also a "CLEAN COVER CACHE" entry in the BIOS power menu (F12).

### Screen recording (MP4 / GIF)

Press **Ctrl+R** anywhere in py-16 to start recording. A small red REC
indicator with a seconds counter appears in the top-right corner. Press
Ctrl+R again to stop — the recording is saved in `~/.py16/recordings/`.

**Format:** MP4 by default (recommended), GIF as fallback.

- **MP4 (preferred):** ~5-10x smaller than GIF, better quality, plays on
  every browser/social platform. Output is 4x upscaled (1024x896) with
  nearest-neighbor for crisp pixels on YouTube, Twitter, etc.
- **GIF (fallback):** native 256x224, 256-color palette, plays inline
  on Reddit and Discord without a player.

Install MP4 support with: `pip install imageio imageio-ffmpeg`. Without
those, py-16 falls back to GIF automatically.

You can override the format in `~/.py16/config.json`:
```json
{ "recording_format": "mp4" }    // or "gif" or "auto" (default)
```

**Other details:**
- Captures at ~30 fps (every other engine frame)
- Auto-stops after 60 seconds (configurable) to bound RAM
- A 30-second MP4 typically lands at 500 KB - 2 MB
- A 30-second GIF typically lands at 2-5 MB
- The REC indicator is drawn after frame capture, so it does NOT appear
  in the exported file — the recording is just your raw cart visuals

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

### Sample playback

In addition to the 4 synthesized waveforms, py-16 has 16 sample slots
that can hold short `.ogg` or `.wav` audio clips (max 256 KB each).
Samples are pitch-shifted on playback like a real sampler — higher
notes shorten the clip, lower notes stretch it.

```python
# Load a sample from disk into slot 0
py16.load_sample(0, "drums/kick.ogg", base_note=24, name="KICK")

# Play it directly (pitched at the slot's base note)
py16.play_sample(0)

# Play at a different pitch (shift up an octave)
py16.play_sample(0, note=36)
```

Samples are also usable as instruments in SFX patches and music tracks.
Instrument numbers 8-23 reference sample slots 0-15. So if you load a
kick drum into slot 0, you can use INST=8 in any SFX cell to trigger
that kick at the cell's note pitch — perfect for making drum patterns
in the music editor.

The samples are embedded in the cart file (base64 in the JSON / PDF
attachment), so a single `.pdf` cart contains everything: code, sprites,
maps, music, and samples.

Needs `pip install pygame` (already a hard dependency, no extra setup).
For loading `.ogg` files, you might need `pip install pygame[mixer]` on
some systems.

### Splitscreen (couch multiplayer)

Render each player into their own viewport with their own camera.
Classic Mario Kart / GoldenEye / Streetfighter layout.

```python
def draw():
    py16.split_layout("horizontal")       # 2 viewports side-by-side
    for p in range(2):
        py16.viewport(p + 1)                # 1 = left, 2 = right
        py16.camera(player_x[p] - 64,
                    player_y[p] - 56)
        draw_world()                         # tiles render inside viewport
        draw_player(p)
        # Per-viewport HUD - stays at top-left of viewport, not world:
        wx, wy = py16.viewport_local(4, 4)
        py16.text(f"P{p+1} {scores[p]}", wx, wy, 11)
    py16.viewport(0)                        # full screen for shared overlay
    draw_shared_hud_over_both_views()
```

Layouts:
- `"full"` — single fullscreen viewport (default, like before)
- `"horizontal"` — 2 viewports side-by-side (Mario Kart 2P)
- `"vertical"` — 2 stacked viewports (split horizontally)
- `"quad"` — 2x2 grid for 3-4 players (GoldenEye style)

Each viewport keeps its own camera. Switching viewport saves and
restores the camera automatically, so `for p in range(N): viewport(p+1);
camera(...)` works as expected.

`viewport(0)` is the special "no-clip" mode: the next draws will cover
the whole screen. Use this for shared HUD elements on top of all
viewports, divider lines between them, or end-of-game overlays.

`viewport_local(x, y)` returns world coordinates that land at local
position (x, y) of the active viewport regardless of where the camera
is looking. Use it for per-viewport HUDs that stay attached to the
viewport's corner while the player walks around.

A 2-player exploration demo with coin collecting is in
`examples/splitscreen_demo.py`. Combined with gamepad support, two
people can play on the same TV with their own gamepads.

### Scanlines (HDMA-style distortion)

Post-process the finished frame by shifting each row horizontally, just
like SNES HDMA used to. Classic use cases: water waves, heat shimmer,
boss-aura lens distortion, CRT-style interlacing, Hadouken shockwaves.

```python
def draw():
    py16.cls(13)                              # sky
    draw_world()                              # will get distorted

    # Apply wave distortion to everything below the horizon:
    wave = py16.scanline_wave(time=frame,
                              amplitude=5, frequency=0.2,
                              y_start=128)
    py16.scanline_apply(x_offsets=wave, wrap=True)

    draw_hud()                                # drawn on top, stays straight
```

Built-in helpers each return a list of `HEIGHT` offsets, one per row:

| Helper | Use case |
|---|---|
| `scanline_wave(time, ...)` | Water surface, ghost backgrounds, swaying flags |
| `scanline_jitter(amplitude, seed)` | Heat shimmer, TV static, broken hologram |
| `scanline_lens(center_y, ...)` | Boss aura, magic glow, fish-eye lens |
| `scanline_interlace(odd, even)` | CRT-look, glitch effects, retro boot screens |
| `scanline_pinch(time, ...)` | Breathing/pulsing whole-screen distortion |

Each helper accepts `y_start` and `y_end` to limit the effect to a
vertical region — apply waves only below the water line, lens only
around the boss, etc.

`scanline_apply(x_offsets, wrap=True)` makes wrapped rows: pixels that
fall off one edge reappear on the other. With `wrap=False`, the gap
gets filled with `fill_color` (default black).

Difference from Mode-7 scanline effects: Mode 7's `scanline_offsets_x`
distorts the perspective ground plane *while it renders*. The scanline
system here distorts the **finished framebuffer** post-render, so it
affects sprites, maps, and everything else you drew. Both systems can
be combined.

Performance: with numpy, ~485 FPS even with a wave applied every frame.
Without numpy, ~120 FPS. Works on Pi 4 without slowdown.

A live demo is in `examples/scanlines_demo.py`.

### Particles (fire, smoke, sparks, explosions, confetti)

Built-in particle system with physics (velocity, acceleration, drag),
lifetime, color, size, and blending. 2000 simultaneous particles fit
in the engine.

```python
# One-shot burst
py16.burst_explosion(x, y, color=8)         # additive boom + flash
py16.burst_sparks(x, y, color=10)           # gravity-affected
py16.burst_smoke(x, y, color=5)             # rising, alpha-blended
py16.burst_confetti(x, y, count=30)         # colourful, falling

# Continuous emitter (fire, fountain, torch, smokestack)
torch = py16.Emitter(
    x=100, y=200,
    rate=4,                      # particles per frame
    life=30, life_var=0.3,
    vy=-2.0, vy_var=0.4,
    vx_var=0.5,
    ay=-0.05,                    # tiny upward acceleration
    color_list=[8, 9, 10],       # red, orange, yellow flicker
    size=2,
    blend="add")                 # additive glow

def update():
    torch.update()               # spawn new particles
    py16.particles_update()      # physics for all live particles

def draw():
    py16.cls(0)
    draw_world()
    py16.particles_draw()        # render all particles
    draw_hud()
```

A particle has position, velocity, acceleration, lifetime, color,
size, blend mode, and drag. Hand-crafted bursts via `py16.particle()`
or `py16.burst()` give full control; presets like `burst_explosion`
cover common cases in one line.

Performance: with numpy installed, 2000 particles run at 200+ FPS on
desktop, 60+ FPS on a Pi 4. Without numpy, 500 particles are smooth.
The engine groups particles by blend mode before drawing to minimise
GPU state switches.

A live showcase is in `examples/particles_demo.py` — fire, fountain,
and on-demand bursts triggered by buttons.

### Blending (color math)

Like the SNES "Color Math" feature, py-16 supports four blending modes
for stacking overlapping draws:

```python
py16.blend_mode("normal")                # default - draws stack normally
py16.blend_mode("add")                   # additive - colors brighten
py16.blend_mode("sub")                   # subtractive - colors darken
py16.blend_mode("alpha", alpha=128)      # transparent (0..255)
```

Use cases:
- **Additive:** plasma effects, magic spells, fire, glow around lights,
  explosion bursts. Overlapping reds + greens + blues turn white.
- **Subtractive:** shadows, eclipse, sunglasses tint. Removes color
  from a bright background.
- **Alpha:** ghost sprites, water surfaces, UI overlays, fade-ins.

The blend mode is a global state that affects subsequent `rectfill`,
`circfill`, `spr`, and `text` calls (outline ops and `cls` are
unaffected). Switch back to `"normal"` before drawing UI text on top:

```python
def draw():
    py16.cls(0)
    draw_world()                          # normal
    py16.blend_mode("add")
    draw_light_sources()                  # glow effect
    py16.blend_mode("normal")
    draw_hud()                            # crisp UI
```

Pygame's hardware blending makes this fast — 3000+ FPS even with 40
overlapping additive circles per frame. A live demo of all four modes
is in `examples/blend_demo.py`.

### Multi-layer maps (SNES BG1-BG4 style)

py-16 has 4 independent map layers, like the SNES had 4 background
planes. Each layer is its own 128x128 tile map; the cart code chooses
which layers to draw and in what order. Classic use:

| Layer | Typical role |
|---|---|
| 0 | Distant background — slow-parallax mountains, sky details |
| 1 | Mid background — clouds, far buildings |
| 2 | Gameplay terrain — the actual playable level |
| 3 | Foreground — vegetation in front of the player, fog |

```python
def draw():
    py16.cls(13)                          # base sky color

    # Distant mountains, slow parallax (0.2x speed)
    py16.draw_map(int(cam_x*0.2)//8, 0, ..., layer=0)

    # Clouds, slower parallax (0.5x)
    py16.draw_map(int(cam_x*0.5)//8, 0, ..., layer=1)

    # Gameplay terrain (1:1 scroll)
    py16.draw_map(int(cam_x)//8, 0, ..., layer=2)

    # Player and entities here
    py16.spr(player_id, x, y)

    # Foreground grass (drawn over the player)
    py16.draw_map(int(cam_x)//8, 0, ..., layer=3)
```

**API:** `mset`, `mget`, `mclear`, `draw_map` all take an optional
`layer=0..3` parameter. Default is layer 0, so existing single-layer
carts work unchanged.

**Map editor:** F2 opens the editor. Press **1, 2, 3, 4** to switch
between the active layers. The currently-edited layer is shown as
"L1"-"L4" in the title bar; tabs in the top right show which layer
you're on. Inactive layers are dimmed in the background so you can
see how your work fits with what's below/above.

**Cart format:** layers are stored only if non-empty, so a cart that
only uses layer 0 stays the same size as before. Old carts without a
`map_layers` field load fine — extra layers are simply zero.

**Mode 7:** `py16.mode7(..., layer=N)` lets you choose which layer
becomes the ground plane texture, e.g. for switching between racing
tracks in different game modes.

A working parallax demo is in `examples/parallax_demo.py`.

### Mode 7 (perspective ground plane)

The classic SNES Mode 7 effect: project the tile map onto a
perspective-distorted ground plane that fluchtes into the distance.
Used in Super Mario Kart, F-Zero, Pilotwings.

```python
def draw():
    py16.cls(12)                          # blue sky
    py16.mode7(cam_x, cam_y, angle,
               horizon_y=80,              # screen Y of horizon line
               cam_height=30,             # camera height above ground
               focal_length=70,           # FOV-ish (smaller = wider)
               sky_color=None)            # already drew our own sky
    # ...draw player car / sprites on top
```

The map (`mset/mget`, 128x128 tiles) becomes the ground texture. With
numpy installed, this renders at 60+ FPS even when the camera moves
and rotates every frame. Without numpy, a slower fallback is used
(every 2nd pixel, still playable).

A working drivable demo is in `examples/mode7_demo.py`.

#### Per-scanline effects

The classic Mode-7 trick: each scanline can use a slightly different
camera angle or position, producing wobble, shake, twist, and curve
effects that defined SNES games like F-Zero and Pilotwings.

```python
n_rows = py16.HEIGHT - horizon_y

# Heat / water shimmer
wave = py16.mode7_wave(n_rows, time=frame * 0.1, amplitude=6)
py16.mode7(cx, cy, angle, scanline_offsets_x=wave, ...)

# Screen shake (boss impact, explosion)
ox, oy = py16.mode7_earthquake(n_rows, time=frame, amplitude=4)
py16.mode7(cx, cy, angle, scanline_offsets_x=ox, scanline_offsets_y=oy, ...)

# Wormhole / magic tunnel
twist = py16.mode7_tunnel(n_rows, twist=0.5)
py16.mode7(cx, cy, angle, scanline_angles=twist, ...)

# Winding road (racing games)
curve = py16.mode7_curve(n_rows, time=frame, curvature=0.3)
py16.mode7(cx, cy, angle, scanline_angles=curve, ...)
```

You can also pass your own list/numpy array of length `n_rows` for
fully custom effects. See `examples/mode7_effects.py` for live demos
of all four built-ins.

### Gamepad / joystick support (up to 4 players)

USB gamepads work out of the box. Connect any controller before starting
or hot-plug it during play — py-16 detects it automatically and maps
its inputs to the same logical buttons that the keyboard uses:

| Gamepad | Logical button | Keyboard equivalent |
|---|---|---|
| D-Pad / left analog stick | up/down/left/right | arrow keys |
| A (south face button) | z | Z |
| B (east face button) | x | X |
| X (west face button) | a | A |
| Y (north face button) | s | S |
| Start | enter | Enter |
| Back / Select | space | Space |
| Left shoulder | shift | Shift |

A cart written for the keyboard automatically works on a gamepad. You
don't need a separate code path. `py16.btn('left')` returns True
whether the keyboard arrow is pressed or the gamepad D-Pad is held.

#### Multi-player (couch co-op)

py-16 supports up to 4 players, each with their own gamepad. The first
connected controller becomes Player 1, the second becomes Player 2, etc.
Use the optional `player=N` argument to query a specific player:

```python
def update():
    # Player 1
    if py16.btn('left',  player=1): p1_x -= 2
    if py16.btn('right', player=1): p1_x += 2
    if py16.btnp('z',    player=1): p1_jump()

    # Player 2
    if py16.btn('left',  player=2): p2_x -= 2
    if py16.btn('right', player=2): p2_x += 2
    if py16.btnp('z',    player=2): p2_jump()
```

**Keyboard fallback:** if zero gamepads are connected, the keyboard
is treated as Player 1. Once any gamepad is connected, Player 1 means
that gamepad and the keyboard becomes "any source" only (queryable
with `player=0` or no player argument). Player 2..4 are never the
keyboard, so a multi-player cart can rely on `btn('z', player=2)` to
mean "the second person's gamepad".

**Slot management API:**

```python
py16.player_count()              # how many players have a controller
py16.player_connected(N)         # is player slot N filled? (1..4)
py16.player_name(N)              # name of P_N's controller, or None
py16.num_controllers()           # total connected (== player_count())
py16.MAX_PLAYERS                 # 4
```

When a controller is unplugged its slot becomes empty; the cart can
detect this with `player_connected(N)` and pause until they reconnect.
Reconnection fills the lowest free slot.

**For Pi-console builds** where there's no F12 key on hand: pressing
**Start + Back simultaneously** on any gamepad triggers BIOS exit,
equivalent to F12.

py-16 uses pygame's higher-level Controller API which consults SDL2's
gamepad mapping database, so most controllers work without manual
configuration. Exotic controllers fall back to a generic Joystick
mapping (button 0 → z, button 1 → x, etc.).

A 2-player Pong demo is in `examples/pong2p.py`.

### Editors at runtime

| Key | Effect |
|---|---|
| F1 | Toggle sprite editor |
| F2 | Toggle map editor |
| F3 | Toggle SFX editor |
| F4 | Toggle music editor |
| F6 | Toggle code editor |
| F7 | Toggle PDF editor (cover/title/author before PDF export) |
| F10 | Toggle sample editor (load .ogg/.wav into 16 sample slots) |
| F9 | Reload cart code (in editor: run code) |
| F11 | Toggle fullscreen |
| F12 | Back to BIOS (universal escape) |
| F5 | Save cart (`.p16` AND `.pdf` in parallel) |
| F8 | Load cart (prefers `.pdf`, if back to `.p16`) |
| ESC | Leave editor / quit game |

**Code editor:** Full-featured text editor with cursor, selection,
copy/cut/paste (Ctrl+C/X/V), undo/redo (Ctrl+Z/Y), search (Ctrl+F),
auto-indent, Tab/Shift-Tab. Ctrl+S writes to the external `.py` file.
F9 recompiles cart code at runtime and replaces `update`/`draw` -
no program restart needed.

**PDF editor (F7):** Live preview of the cover page with editable
metadata. Edit title, author, cover style, colors, font, and text
styling before saving as PDF. Three tabs:

- **META** - title, author, cover style (sheet/map/screenshot/custom)
- **STYLE** - colors (background/title band/title text/author text),
  font (helvetica/courier/times/pixel), plus per-text styling:
  - Title: size (14-48pt), bold, italic, underline
  - Author: size (8-24pt), bold, italic, underline
- **IMAGE** - load custom PNG/JPG to embed as cover (max 200KB)

Use **arrow keys** to navigate fields, **left/right** to cycle values,
**Space** to toggle bool fields. **Q/W** switch tabs.

Bold+Italic combinations work — each font family has all 4 variants
(regular, bold, italic, bold-italic) plus an underline option drawn
as a line under the text. So a title can be e.g. Times bold-italic
underline at 38pt while the author below is Helvetica italic at 14pt.

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

**Load (F8):** prefers `.pdf` (if present), if back to `.p16`.
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
