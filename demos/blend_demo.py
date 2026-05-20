"""
BLENDING DEMO for py-16
========================

Showcase of the four blend modes: normal, additive, subtractive, alpha.
Press Z to cycle through them.

# @manual
# @description
# Demonstrates py16.blend_mode() with classic light/dark effects.
# Watch overlapping circles add up to white in additive mode, or
# subtract from a bright background in subtractive mode.
#
# @controls
# Z          : Next blend mode
# X          : Pause animation
# Arrows     : Move the cursor light
# F12        : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import math
import py16

MODES = ["NORMAL", "ADD", "SUB", "ALPHA"]
mode_idx = 1     # start with additive (most visually striking)

cursor_x = 128.0
cursor_y = 112.0

paused = False
frame = 0

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

def update():
    global mode_idx, cursor_x, cursor_y, paused, frame

    if py16.btnp('z'):
        mode_idx = (mode_idx + 1) % len(MODES)
    if py16.btnp('x'):
        paused = not paused

    if py16.btn('left'):  cursor_x -= 1.5
    if py16.btn('right'): cursor_x += 1.5
    if py16.btn('up'):    cursor_y -= 1.5
    if py16.btn('down'):  cursor_y += 1.5
    cursor_x = max(8, min(py16.WIDTH - 8, cursor_x))
    cursor_y = max(20, min(py16.HEIGHT - 8, cursor_y))

    if not paused:
        frame += 1

def draw():
    name = MODES[mode_idx]

    # Background depends on mode (sub mode needs light bg, others dark)
    if name == "SUB":
        py16.cls(7)                       # white background
    else:
        py16.cls(1)                       # dark blue background

    # Draw a "scene" first - some stripes to show what's behind the effect
    for i in range(8):
        col = 12 if i % 2 == 0 else 14
        py16.rectfill(i * 32, 60, 16, 120, col)

    # Map blend mode
    mode_name_to_arg = {
        "NORMAL": ("normal", 255),
        "ADD":    ("add", 255),
        "SUB":    ("sub", 255),
        "ALPHA":  ("alpha", 128),
    }
    blend, alpha = mode_name_to_arg[name]
    py16.blend_mode(blend, alpha=alpha)

    # Three rotating circles that overlap in the center
    cx = py16.WIDTH // 2
    cy = py16.HEIGHT // 2 + 10
    radius = 28
    orbit = 18
    for k in range(3):
        ang = frame * 0.02 + k * (2 * math.pi / 3)
        ox = cx + math.cos(ang) * orbit
        oy = cy + math.sin(ang) * orbit
        col = [8, 11, 12][k]            # red, green, blue
        py16.circfill(ox, oy, radius, col)

    # Cursor "light" the player moves around
    light_col = 10 if name != "SUB" else 8
    py16.circfill(cursor_x, cursor_y, 12, light_col)

    # Always switch back to normal for UI overlays
    py16.blend_mode("normal")

    # HUD
    py16.rectfill(0, 0, py16.WIDTH, 12, 0)
    py16.text(f"BLEND: {name}", 4, 3, 11)
    py16.text("Z NEXT  X PAUSE  ARROWS MOVE",
              py16.WIDTH - 138, 3, 6)

    # Info line at the bottom
    info = {
        "NORMAL": "no blending - draws stack normally",
        "ADD":    "additive - colors add up, brighter",
        "SUB":    "subtractive - colors remove, darker",
        "ALPHA":  "50% transparency - see through layers",
    }[name]
    py16.rectfill(0, py16.HEIGHT - 10, py16.WIDTH, 10, 0)
    py16.text(info, 4, py16.HEIGHT - 8, 6)

if __name__ == "__main__":
    py16.run(update, draw, init)
