"""
SCANLINE EFFECTS DEMO for py-16
================================

Cycles through HDMA-style scanline distortions: wave (water), jitter
(heat shimmer), lens (boss aura), interlace (CRT), and pinch.

# @manual
# @description
# Press Z to cycle through scanline effects. The world bends in
# real-time while the HUD stays straight - that's the trick to making
# them feel natural in your own carts.
#
# @controls
# Z          : Next effect
# X          : Strength up
# A          : Strength down
# F12        : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import math
import py16

EFFECTS = ["NONE", "WAVE", "JITTER", "LENS", "INTERLACE", "WATER", "PINCH"]
effect_idx = 1
frame = 0
strength = 1.0

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

    # A simple test scene: tile-style background made of map sprites
    # so the distortion is visible
    for j in range(8):
        for i in range(8):
            # Sprite 1: red
            py16.sset(8 + i,  j, 8)
            # Sprite 2: blue
            py16.sset(16 + i, j, 12)
            # Sprite 3: green
            py16.sset(24 + i, j, 11)
            # Sprite 4: yellow
            py16.sset(32 + i, j, 10)

    # A checkerboard-style map
    for y in range(32):
        for x in range(32):
            if y < 14:
                # sky (no tiles)
                py16.mset(x, y, 0)
            elif y < 16:
                # ground line
                py16.mset(x, y, 3)
            else:
                # alternating water tiles
                py16.mset(x, y, 1 if (x + y) % 2 == 0 else 2)

def update():
    global effect_idx, frame, strength

    if py16.btnp('z'):
        effect_idx = (effect_idx + 1) % len(EFFECTS)
    if py16.btnp('x'):
        strength = min(4.0, strength * 1.5)
    if py16.btnp('a'):
        strength = max(0.25, strength / 1.5)

    frame += 1

def draw():
    # === WORLD: sky + ground + water ===
    py16.cls(13)   # purple sky
    py16.draw_map(0, 0, 0, 0, 32, 32)

    # A "boss" sprite as visual reference
    py16.rectfill(110, 90, 36, 36, 14)   # pink box
    py16.rectfill(118, 100, 4, 4, 0)
    py16.rectfill(134, 100, 4, 4, 0)
    py16.rectfill(118, 116, 20, 4, 0)

    # === APPLY EFFECT ===
    name = EFFECTS[effect_idx]
    s = strength

    if name == "WAVE":
        offs = py16.scanline_wave(time=frame,
                                  amplitude=4 * s,
                                  frequency=0.12,
                                  speed=2.0)
        py16.scanline_apply(x_offsets=offs, wrap=True)

    elif name == "JITTER":
        # Use frame as seed for different jitter each frame
        offs = py16.scanline_jitter(amplitude=2 * s, seed=frame)
        py16.scanline_apply(x_offsets=offs, wrap=True)

    elif name == "LENS":
        # Lens follows a moving center
        cy = 112 + int(math.sin(frame * 0.04) * 30)
        offs = py16.scanline_lens(center_y=cy,
                                  strength=12 * s, radius=40)
        py16.scanline_apply(x_offsets=offs, wrap=True)

    elif name == "INTERLACE":
        offs = py16.scanline_interlace(odd_offset=int(2 * s),
                                       even_offset=-int(2 * s))
        py16.scanline_apply(x_offsets=offs)

    elif name == "WATER":
        # Wave only below the horizon (=ground line at row 128)
        offs = py16.scanline_wave(time=frame,
                                  amplitude=5 * s, frequency=0.2,
                                  speed=3.0,
                                  y_start=128)
        py16.scanline_apply(x_offsets=offs, wrap=True)

    elif name == "PINCH":
        offs = py16.scanline_pinch(time=frame,
                                   amplitude=8 * s, period=120,
                                   y_start=12, y_end=224)
        py16.scanline_apply(x_offsets=offs, wrap=True)

    # === HUD (drawn AFTER apply, stays straight) ===
    py16.rectfill(0, 0, py16.WIDTH, 12, 0)
    py16.text(f"EFFECT: {name}", 4, 3, 11)
    py16.text(f"STR {s:.2f}", py16.WIDTH - 50, 3, 7)
    py16.rectfill(0, py16.HEIGHT - 10, py16.WIDTH, 10, 0)
    py16.text("Z NEXT  A/X STRENGTH",
              4, py16.HEIGHT - 8, 6)

if __name__ == "__main__":
    py16.run(update, draw, init)
