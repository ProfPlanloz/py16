"""
MODE 7 SCANLINE EFFECTS for py-16
==================================

Toggle through the four built-in scanline effects to see them
animated. Use this as a reference for building your own effects.

# @manual
# @description
# Cycles through Mode-7 scanline effects: wave, earthquake, tunnel
# and curve. Press Z to step through, X to reset to no effect.
#
# @controls
# Z          : Next effect
# X          : No effect (plain Mode 7)
# Arrows     : Pan camera
# F12        : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import math
import py16

EFFECTS = ["NONE", "WAVE", "EARTHQUAKE", "TUNNEL", "CURVE"]
effect_idx = 1            # start with wave
cam_x = 512.0
cam_y = 512.0
frame = 0

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

    # Sprites: red, blue, white grid
    for j in range(8):
        for i in range(8):
            py16.sset(8 + i,  j, 8)
            py16.sset(16 + i, j, 12)
            py16.sset(24 + i, j, 7)

    # Checkerboard with grid lines
    for y in range(128):
        for x in range(128):
            if (x % 4 == 0) or (y % 4 == 0):
                py16.mset(x, y, 3)
            elif (x // 4 + y // 4) % 2 == 0:
                py16.mset(x, y, 1)
            else:
                py16.mset(x, y, 2)

def update():
    global effect_idx, cam_x, cam_y, frame

    if py16.btnp('z'):
        effect_idx = (effect_idx + 1) % len(EFFECTS)
    if py16.btnp('x'):
        effect_idx = 0

    # Camera pan with arrows
    if py16.btn('left'):  cam_x -= 3
    if py16.btn('right'): cam_x += 3
    if py16.btn('up'):    cam_y -= 3
    if py16.btn('down'):  cam_y += 3

    frame += 1

def draw():
    horizon = 80
    n_rows = py16.HEIGHT - horizon
    py16.cls(12)

    name = EFFECTS[effect_idx]

    if name == "NONE":
        py16.mode7(cam_x, cam_y, 0,
                   horizon_y=horizon, cam_height=40,
                   focal_length=80, sky_color=12)

    elif name == "WAVE":
        wave = py16.mode7_wave(n_rows, time=frame * 0.1,
                               amplitude=8, frequency=0.3, speed=2.0)
        py16.mode7(cam_x, cam_y, 0,
                   horizon_y=horizon, cam_height=40,
                   focal_length=80, sky_color=12,
                   scanline_offsets_x=wave)

    elif name == "EARTHQUAKE":
        ox, oy = py16.mode7_earthquake(n_rows, time=frame * 0.3,
                                       amplitude=4, decay=True)
        py16.mode7(cam_x, cam_y, 0,
                   horizon_y=horizon, cam_height=40,
                   focal_length=80, sky_color=12,
                   scanline_offsets_x=ox,
                   scanline_offsets_y=oy)

    elif name == "TUNNEL":
        twist_amount = 0.6 * math.sin(frame * 0.05)
        twist = py16.mode7_tunnel(n_rows, twist=twist_amount)
        py16.mode7(cam_x, cam_y, 0,
                   horizon_y=horizon, cam_height=40,
                   focal_length=80, sky_color=13,
                   scanline_angles=twist)

    elif name == "CURVE":
        curve = py16.mode7_curve(n_rows, time=frame * 1.0,
                                 curvature=0.4, period=30)
        py16.mode7(cam_x, cam_y, 0,
                   horizon_y=horizon, cam_height=40,
                   focal_length=80, sky_color=12,
                   scanline_angles=curve)

    # HUD
    py16.rectfill(0, 0, py16.WIDTH, 12, 0)
    py16.text(f"EFFECT: {name}", 4, 3, 11)
    py16.text("Z NEXT  X RESET  ARROWS PAN",
              py16.WIDTH - 132, 3, 6)

if __name__ == "__main__":
    py16.run(update, draw, init)
