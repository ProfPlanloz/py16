"""
PARTICLE DEMO for py-16
========================

Multiple particle effects on screen at once:
  - Continuous fire on the left
  - Continuous fountain on the right
  - On-demand explosion, sparks, confetti

# @manual
# @description
# Particle system showcase. A fire and a fountain run continuously.
# Press buttons to fire one-shot effects at the cursor.
#
# @controls
# Arrows       : Move cursor
# Z            : Explosion at cursor
# X            : Sparks at cursor
# A            : Confetti at cursor
# S            : Smoke at cursor
# F12          : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import math
import py16

cursor_x = 128.0
cursor_y = 112.0
frame = 0
fire   = None
fountain = None

def init():
    global fire, fountain
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

    # Continuous fire on the left
    fire = py16.Emitter(x=60, y=190,
                        rate=4,
                        life=28, life_var=0.3,
                        vy=-2.0, vy_var=0.4,
                        vx_var=0.5,
                        ay=-0.05,
                        color_list=[8, 9, 10],   # red, orange, yellow
                        size=2,
                        blend="add")

    # Continuous fountain on the right
    fountain = py16.Emitter(x=200, y=180,
                            rate=3,
                            life=80, life_var=0.2,
                            vy=-3.5, vy_var=0.3,
                            vx_var=1.2,
                            ay=0.1,                # gravity falls
                            drag=0.99,
                            color_list=[6, 12, 7], # light blue/white
                            size=1,
                            blend="alpha")

def update():
    global cursor_x, cursor_y, frame
    frame += 1

    if py16.btn('left'):  cursor_x -= 2
    if py16.btn('right'): cursor_x += 2
    if py16.btn('up'):    cursor_y -= 2
    if py16.btn('down'):  cursor_y += 2
    cursor_x = max(8, min(py16.WIDTH - 8, cursor_x))
    cursor_y = max(20, min(py16.HEIGHT - 16, cursor_y))

    if py16.btnp('z'):
        py16.burst_explosion(cursor_x, cursor_y)
    if py16.btnp('x'):
        py16.burst_sparks(cursor_x, cursor_y, color=10)
    if py16.btnp('a'):
        py16.burst_confetti(cursor_x, cursor_y)
    if py16.btnp('s'):
        py16.burst_smoke(cursor_x, cursor_y)

    fire.update()
    fountain.update()
    py16.particles_update()

def draw():
    py16.cls(0)

    # Ground line
    py16.rectfill(0, 200, py16.WIDTH, 24, 3)

    # Markers for the continuous emitters
    py16.rectfill(56, 196, 8, 8, 5)     # fire base (gray block)
    py16.rectfill(196, 178, 8, 4, 6)    # fountain base (gray block)

    # All particles
    py16.particles_draw()

    # Cursor: crosshair
    cx = int(cursor_x)
    cy = int(cursor_y)
    py16.line(cx - 5, cy, cx - 2, cy, 7)
    py16.line(cx + 2, cy, cx + 5, cy, 7)
    py16.line(cx, cy - 5, cx, cy - 2, 7)
    py16.line(cx, cy + 2, cx, cy + 5, 7)

    # HUD
    py16.rectfill(0, 0, py16.WIDTH, 12, 0)
    py16.text("PARTICLES DEMO", 4, 3, 11)
    py16.text(f"{py16.particles_count():4d}/{py16.MAX_PARTICLES}",
              py16.WIDTH - 50, 3, 6)

    # Help line
    py16.rectfill(0, py16.HEIGHT - 10, py16.WIDTH, 10, 0)
    py16.text("Z BOOM  X SPARKS  A CONFETTI  S SMOKE",
              4, py16.HEIGHT - 8, 6)

if __name__ == "__main__":
    py16.run(update, draw, init)
