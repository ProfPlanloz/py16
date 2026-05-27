# py-16 API Cheatsheet for AI Assistants

> **Use this as a system prompt when asking an AI to write a py-16 cart.**
> It gives the AI the exact API surface so it doesn't hallucinate functions.

## What py-16 is

A 16-bit-era fantasy console for Python. You write `update()` and `draw()`
functions, the engine runs them at 60 FPS. Carts are single Python files.

## Cart skeleton (every cart needs this)

```python
import py16

# Module-level state goes here (no classes required)
x, y = 64, 100

def init():
    """Called once at startup. Set up sprites, map, sound, etc."""
    pass

def update():
    """Called every frame, before draw. Handle input + game logic."""
    global x, y
    if py16.btn('left'):  x -= 1
    if py16.btn('right'): x += 1

def draw():
    """Called every frame. Draw everything. Don't update game state here."""
    py16.cls(0)
    py16.spr(1, x, y)
    py16.text("HELLO", 4, 4, 7)

if __name__ == "__main__":
    py16.run(update, draw, init)
```

## Display: 256 wide, 224 high. 60 FPS. 256 colors, palette indexed.

```python
py16.WIDTH      # 256
py16.HEIGHT     # 224
py16.FPS        # 60
```

## Drawing primitives (color = palette index 0-255)

```python
py16.cls(c=0)                              # clear screen
py16.pset(x, y, c)                         # one pixel
py16.rect(x, y, w, h, c)                   # outlined rectangle
py16.rectfill(x, y, w, h, c)               # filled rectangle (blendable)
py16.line(x0, y0, x1, y1, c)               # line
py16.circ(x, y, r, c)                      # outlined circle
py16.circfill(x, y, r, c)                  # filled circle (blendable)
py16.text(s, x, y, c=7)                    # 3x5 pixel text (blendable)
py16.camera(x, y)                          # camera offset for all draws
py16.clip(x, y, w, h)                      # scissor rect, no args = reset
py16.pal(c0, c1)                           # color remap (c0 -> c1 on draw)
py16.palt(c, transparent=True)             # mark color as transparent
```

## Blending (color math / transparency)

```python
py16.blend_mode("normal")                  # default, no blending
py16.blend_mode("add")                     # additive  (glow, plasma, fire)
py16.blend_mode("sub")                     # subtractive (shadows, eclipse)
py16.blend_mode("alpha", alpha=128)        # 0..255 transparency (ghosts, water)
```

Affects `rectfill`, `circfill`, `spr`, `text`. Outline ops (`rect`,
`circ`, `line`) and `cls` are unaffected. Switch back to `"normal"`
before drawing UI. Pygame's hardware blending = 3000+ FPS even with
40+ overlapping additive circles per frame.

## Particles (fire, smoke, sparks, explosions, confetti)

```python
# One-off particle
py16.particle(x, y, vx=0, vy=0,
              life=60, color=7, size=1,
              ax=0.0, ay=0.0,       # acceleration / gravity
              drag=1.0,              # velocity multiplier
              blend="normal")        # "normal" | "add" | "sub" | "alpha"

# Burst from a single point (count particles radiating outward)
py16.burst(x, y, count=20, color=8, life=30, speed=2.0,
           size=1, spread_angle=2*pi, base_angle=0,
           ax=0, ay=0, drag=1.0, blend="normal",
           speed_var=0.5, life_var=0.5)

# Presets (one-line common effects)
py16.burst_explosion(x, y, color=8)     # add-blended boom + flash
py16.burst_sparks(x, y, color=10)       # gravity-affected spray
py16.burst_smoke(x, y, color=5)         # rising, alpha-blended
py16.burst_confetti(x, y, count=30)     # multi-color falling

# Continuous emitter (call .update() each frame)
fire = py16.Emitter(x=100, y=200,
                    rate=4,              # particles per frame
                    life=30, life_var=0.3,
                    vy=-2.0, vy_var=0.4,
                    ay=-0.05,
                    color_list=[8, 9, 10],   # red/orange/yellow
                    size=2, blend="add")
fire.update()                  # in your update()
fire.emit = False              # pause emission

# Required once per frame:
py16.particles_update()        # physics tick
py16.particles_draw()          # render all particles
py16.particles_count()         # how many alive
py16.particles_clear()         # remove all
```

Performance: 2000 particles at 200+ FPS on desktop, 60+ FPS on Pi 4
with numpy installed. Without numpy, ~500 particles run smoothly.

## Scanlines (HDMA-style horizontal distortion)

Post-process the rendered frame by shifting each row horizontally,
like SNES HDMA. Used for water, heat shimmer, lens distortion, CRT.

```python
def draw():
    py16.cls(12)
    draw_world()                              # gets distorted

    # Apply effect to everything drawn so far:
    wave = py16.scanline_wave(time=frame, amplitude=4, frequency=0.1)
    py16.scanline_apply(x_offsets=wave, wrap=True)

    draw_hud()                                # stays straight

# Helpers (each returns a list of HEIGHT row offsets):
py16.scanline_wave(time, amplitude=4, frequency=0.1, speed=2,
                   y_start=0, y_end=None)         # smooth sine wave
py16.scanline_jitter(amplitude=2, seed=None)      # random per-row shake
py16.scanline_lens(center_y, strength=8, radius=40)  # convex bulge
py16.scanline_interlace(odd_offset=1, even_offset=-1)  # CRT artifact
py16.scanline_pinch(time, amplitude=2, period=60)  # full-screen breathing

# Apply options:
py16.scanline_apply(x_offsets, wrap=False, fill_color=0)
#   wrap=True   : pixels wrap around (seamless waves)
#   wrap=False  : gap filled with fill_color (default black)
```

`y_start`/`y_end` on helpers limit the effect to a vertical region —
use `y_start=horizon_y` to only wave the water below the horizon.

## Splitscreen (couch multiplayer)

Render each player into their own viewport with independent cameras:

```python
def draw():
    py16.split_layout("horizontal")     # "full"|"horizontal"|"vertical"|"quad"
    for p in range(2):
        py16.viewport(p + 1)              # 1..4 = each player's view
        py16.camera(players[p].x - 64,
                    players[p].y - 56)
        draw_world()                       # draws inside this viewport only
        draw_player(p)
        # Per-viewport HUD label that stays put while camera scrolls:
        wx, wy = py16.viewport_local(4, 4)
        py16.text(f"P{p+1}", wx, wy, 11)
    py16.viewport(0)                      # back to full screen
    draw_shared_hud()                     # over all viewports

py16.num_viewports()                      # 1, 2 or 4
py16.viewport_rect(idx)                   # (x, y, w, h) in screen pixels
py16.for_each_player(callback)            # convenience loop
```

Layouts: `"full"` (1 vp), `"horizontal"` (2 side-by-side), `"vertical"`
(2 stacked), `"quad"` (2x2 for 3-4 players). `viewport(0)` is special:
it removes clipping, used for shared HUD on top of all viewports.

Each viewport keeps its own camera - switching viewports saves/restores
it. `viewport_local(x, y)` returns world coordinates that land at
local viewport position (x, y) regardless of the camera, perfect for
per-viewport HUDs.

## Useful palette indices (first 16 are Pico-8-compatible)

| Idx | Color   | Idx | Color  |
|-----|---------|-----|--------|
|  0  | black   |  8  | red    |
|  1  | dk-blue |  9  | orange |
|  2  | dk-purple| 10 | yellow |
|  3  | dk-green| 11  | green  |
|  4  | brown   | 12  | blue   |
|  5  | dk-grey | 13  | indigo |
|  6  | lt-grey | 14  | pink   |
|  7  | white   | 15  | peach  |

Indices 16-31 are 16 grayscales. 32-247 are a 6×6×6 RGB cube. The full
palette is `py16.PALETTE` (list of (r,g,b) tuples).

## sprites (1024 slots, each 8x8 pixels)

```python
py16.sset(x, y, c)                         # set pixel in sprite sheet
py16.sget(x, y)                            # get palette index from sheet
py16.spr(id, x, y, w=1, h=1, flip_x=False, flip_y=False)
                                           # draw sprite at (x,y)
                                           # w/h in 8x8 cells (multi-cell)
py16.load_spritesheet("file.png")          # quantize image into sheet
```

## Map (128x128 tiles, each tile is a sprite ID, up to 4 layers)

```python
# Layer parameter is optional, default 0 (back-compat with single-layer carts)
py16.mset(cx, cy, sprite_id, layer=0)      # set tile on layer 0..3
py16.mget(cx, cy, layer=0)                 # get tile id (0 = empty)
py16.mclear(layer=0)                       # wipe entire layer
py16.draw_map(cx, cy, sx, sy, w, h,
              layer_flag=-1, layer=0)      # draw region from a layer
                                           # layer_flag: only sprites with
                                           # the given flag bit set (0..7)

# 4 layers like SNES BG1-BG4. Render order is up to you:
#   draw_map(layer=0)       <- back: distant mountains, sky parallax
#   draw_map(layer=1)       <- mid:  clouds, mid-range parallax
#   spr(...) for entities
#   draw_map(layer=2)       <- gameplay tiles (terrain, blocks)
#   draw_map(layer=3)       <- foreground: vegetation, fog, UI overlays

# Mode 7 perspective ground plane (Mario Kart / F-Zero style):
py16.mode7(cam_x, cam_y, angle,
           horizon_y=64,                   # screen Y of horizon
           cam_height=32, focal_length=64, # camera distortion controls
           sky_color=None,                 # palette idx, fills above horizon
           scanline_angles=None,           # per-row angle offsets (list/array)
           scanline_offsets_x=None,        # per-row X offsets
           scanline_offsets_y=None,        # per-row Y offsets
           layer=0)                        # which map layer to project

# Helpers that produce per-scanline arrays for common effects:
n_rows = py16.HEIGHT - horizon_y
py16.mode7_wave(n_rows, time, amplitude, frequency, speed)  # heat / water shimmer
py16.mode7_earthquake(n_rows, time, amplitude)              # screen shake
py16.mode7_tunnel(n_rows, twist)                            # wormhole / magic effect
py16.mode7_curve(n_rows, time, curvature, period)           # winding road
```

## Sprite flags (8 bit-flags per sprite, 0-7)

```python
py16.fset(sprite_id, flag, True/False)     # set flag
py16.fget(sprite_id, flag)                 # check flag
py16.fget(sprite_id)                       # get all 8 flags as int
```

Common pattern: flag 0 = solid (collide), flag 1 = enemy, flag 2 = item.

## Input (string keys, NOT pygame constants)

```python
py16.btn('left' | 'right' | 'up' | 'down' | 'z' | 'x' |
         'a' | 's' | 'w' | 'd' | 'q' | 'e' |
         'space' | 'enter' | 'shift')
                                           # held this frame?
py16.btnp(...)                             # just pressed this frame?
py16.mouse_x()                             # 0..WIDTH-1
py16.mouse_y()                             # 0..HEIGHT-1
py16.mouse_btn(0|1|2)                      # 0=left, 1=middle, 2=right
py16.mouse_btnp(0|1|2)                     # just clicked?
```

**Multi-player:** btn/btnp accept an optional `player=N` argument:
```python
py16.btn('left', player=1)                 # only P1's gamepad (or keyboard
                                           # fallback if no gamepads)
py16.btn('left', player=2)                 # only P2's gamepad
py16.btn('left', player=0)                 # any source (default, back-compat)

py16.player_count()                        # how many players have a controller
py16.player_connected(N)                   # is player slot N filled? (1..4)
py16.player_name(N)                        # name of P_N's controller, or None
py16.MAX_PLAYERS                           # 4
```

**Gamepad note:** USB gamepads automatically map to the same logical
buttons. D-Pad / left analog stick → directions, A/B/X/Y face buttons →
z/x/a/s, Start → enter, Back → space, LB → shift. So a cart written
for keyboard works on a gamepad without any extra code.

## Sound

```python
# SFX patches (0..63), set up in SFX editor or programmatically:
py16.sfx(patch_id, channel=-1)             # play SFX patch (channel 4-7 used)
py16.music(track_id)                       # play music track 0..7 in background
py16.music(-1)                             # stop music

# Quick raw tones (no SFX patch needed):
py16.tone(pitch_hz, duration_ms, wave, channel=-1,
          pulse_width=0.5,                    # 0.125, 0.25, 0.5, 0.75
          attack_ms=0, decay_ms=0,            # ADSR envelope (ms)
          sustain=1.0, release_ms=0)
# wave = py16.WAVE_SQUARE | py16.WAVE_TRIANGLE | py16.WAVE_SAW | py16.WAVE_NOISE

# Sample playback (16 sample slots, .ogg or .wav files, max 256 KB each):
py16.load_sample(slot, "kick.ogg", base_note=24, name="KICK")  # load into slot
py16.play_sample(slot, note=24)            # play at given pitch (note=None = base pitch)
py16.set_sample_base_note(slot, 30)        # change pitch reference
# Samples are also usable as instruments 8..23 in SFX patches and music tracks.
```

## Math helpers

```python
py16.rnd(max=1.0)                          # random float 0..max
py16.flr(v)                                # floor
py16.ceil(v)                               # ceiling
py16.abs_(v)                               # abs (note underscore!)
py16.mid(a, b, c)                          # middle of 3 values (clamp)
py16.sin(rad), py16.cos(rad), py16.atan2(y, x)
py16.sqrt(v)
py16.t()                                   # frame counter
py16.fps()                                 # current FPS
```

## Cart state and lifecycle

```python
py16.set_cart_code(code_string)            # programmatic code load
py16.set_code_file(path)                   # link code editor to .py file
py16.save_cart("game.p16")                 # save cart
py16.save_cart("game.pdf")                 # save as PDF with manual
py16.export_pdf("game.pdf", title=, author=)  # explicit PDF export
py16.load_cart("game.p16")                 # load (also handles .pdf)

# Cart switching at runtime:
py16.run_cart("other.p16")                 # reset, replace current cart
py16.push_cart("menu.p16")                 # remember current, run other
py16.pop_cart()                            # back to previous cart
py16.go_to_bios()                          # back to BIOS screen
py16.toggle_fullscreen()                   # F11 equivalent
```

## Manual format (for PDF export)

Put this anywhere in the cart code. It will appear on the PDF manual page:

```python
# @manual
# @description
# Brief description of the game.
#
# @controls
# Arrows : Move
# Z      : Jump
#
# @credits
# Code: Your name
# @end
```

## PDF cover styling

The PDF editor (F7) has a STYLE tab where the cover title and author
can be individually styled. These fields can also be set programmatically
in `state.cart_meta`:

```python
state.cart_meta = {
    "title":             "AWESOME GAME",
    "author":            "YOUR NAME",
    "font":              "helvetica",  # helvetica|times|courier|pixel
    # ... colors, cover_style ...
    # Title styling
    "title_size":        32,    # 14..48 (preset sizes)
    "title_bold":        True,
    "title_italic":      False,
    "title_underline":   False,
    # Author styling
    "author_size":       10,    # 8..24
    "author_bold":       True,
    "author_italic":     False,
    "author_underline":  False,
}
```

Bold+Italic combinations work because each font family has all 4
variants (regular/bold/italic/bold-italic). Underline is drawn as a
line below the text baseline.

## Common pitif (please don't make these mistakes)

- **Don't use pygame constants for keys.** Use strings: `py16.btn('left')`
  not `py16.btn(pygame.K_LEFT)`.
- **Don't use `py16.abs()`** - it's `py16.abs_()` with an underscore.
- **Color is an integer 0-255**, not an RGB tuple.
- **Sprite IDs run 0-1023**, indexing the 32x32-sprite sheet (32 per row).
- **Don't update state in `draw()`** — only render. Use `update()` for logic.
- **Globals need `global` keyword** in update/draw if you reassign them.
- **`py16.text()` uppercases by default**; pass `upper=False` to keep case
  (but the font has no real lowercase glyphs - they get rendered as caps).
- **The 3x5 pixel font supports** A-Z, 0-9, `()[]{}<>=+-*/\\:;,.!?&|^~%@#"'$_`
  but **NOT** lowercase glyphs - everything renders uppercase.

## Minimal-Pong example (24 lines, complete cart)

```python
import py16

ball_x, ball_y, dx, dy = 128, 112, 2, 2
paddle_y = 96

def init(): pass

def update():
    global ball_x, ball_y, dx, dy, paddle_y
    if py16.btn('up'):   paddle_y = max(0, paddle_y - 3)
    if py16.btn('down'): paddle_y = min(184, paddle_y + 3)
    ball_x += dx; ball_y += dy
    if ball_y < 0 or ball_y > 220: dy = -dy
    if ball_x > 250: dx = -dx
    if ball_x < 10 and paddle_y < ball_y < paddle_y + 40:
        dx = -dx; py16.tone(440, 50, py16.WAVE_SQUARE)
    if ball_x < 0:
        ball_x, ball_y, dx, dy = 128, 112, 2, 2

def draw():
    py16.cls(1)
    py16.rectfill(4, paddle_y, 4, 40, 7)
    py16.circfill(int(ball_x), int(ball_y), 3, 11)

if __name__ == "__main__":
    py16.run(update, draw, init)
```

That's the entire API. If you stick to these functions and patterns,
your cart will run on py-16.
