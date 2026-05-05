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
py16.rectfill(x, y, w, h, c)               # filled rectangle
py16.line(x0, y0, x1, y1, c)               # line
py16.circ(x, y, r, c)                      # outlined circle
py16.circfill(x, y, r, c)                  # filled circle
py16.text(s, x, y, c=7)                    # 3x5 pixel text
py16.camera(x, y)                          # camera offset for all draws
py16.clip(x, y, w, h)                      # scissor rect, no args = reset
py16.pal(c0, c1)                           # color remap (c0 -> c1 on draw)
py16.palt(c, transparent=True)             # mark color as transparent
```

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

## Sprites (1024 slots, each 8x8 pixels)

```python
py16.sset(x, y, c)                         # set pixel in sprite sheet
py16.sget(x, y)                            # get palette index from sheet
py16.spr(id, x, y, w=1, h=1, flip_x=False, flip_y=False)
                                           # draw sprite at (x,y)
                                           # w/h in 8x8 cells (multi-cell)
py16.load_spritesheet("file.png")          # quantize image into sheet
```

## Map (128x128 tiles, each tile is a sprite ID)

```python
py16.mset(cx, cy, sprite_id)               # set tile at cell (cx,cy)
py16.mget(cx, cy)                          # get tile id (0 = empty)
py16.draw_map(cx, cy, sx, sy, w, h, layer_flag=-1)
                                           # draw map region cx,cy of size w*h
                                           # at screen pos sx,sy
                                           # layer_flag: only draw sprites
                                           # whose flag is set (0..7)
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
         'a' | 's' | 'space' | 'enter' | 'shift')
                                           # held this frame?
py16.btnp(...)                             # just pressed this frame?
py16.mouse_x()                             # 0..WIDTH-1
py16.mouse_y()                             # 0..HEIGHT-1
py16.mouse_btn(0|1|2)                      # 0=left, 1=middle, 2=right
py16.mouse_btnp(0|1|2)                     # just clicked?
```

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

## Common pitfalls (please don't make these mistakes)

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
