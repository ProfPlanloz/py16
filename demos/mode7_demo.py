"""
MODE 7 DEMO for py-16
======================

A simple race-track demo showing the Mode-7 effect. Drive a small
car around a checkerboard ground plane.

# @manual
# @description
# Mode 7 demonstration. Steer a car around a checkerboard plane,
# watch the world rotate and stretch in classic SNES style.
#
# @controls
# Arrow up    : Accelerate
# Arrow down  : Brake / reverse
# Arrow L/R   : Turn
# Z           : Horn
# F12         : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import math
import py16

# Camera state
cam_x = 512.0
cam_y = 512.0
cam_angle = 0.0
speed = 0.0

MAX_SPEED = 6.0
ACCEL     = 0.15
BRAKE     = 0.25
FRICTION  = 0.05
TURN_RATE = 0.04

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

    # Build sprites: red, blue, white (for the checkerboard tiles)
    for j in range(8):
        for i in range(8):
            py16.sset(8 + i,  j, 8)    # sprite 1: red
            py16.sset(16 + i, j, 12)   # sprite 2: blue
            py16.sset(24 + i, j, 7)    # sprite 3: white (grid line)

    # Sprite for the car: little box on top of the screen
    car = [
        "00088000",
        "08888880",
        "08000080",
        "08888880",
        "08888880",
        "08888880",
        "08888880",
        "00808080",
    ]
    for j, row in enumerate(car):
        for i, c in enumerate(row):
            if c != '0':
                py16.sset(32 + i, j, int(c))

    # Build a checkerboard map with grid lines
    for y in range(128):
        for x in range(128):
            if (x % 8 == 0) or (y % 8 == 0):
                py16.mset(x, y, 3)
            elif (x // 8 + y // 8) % 2 == 0:
                py16.mset(x, y, 1)
            else:
                py16.mset(x, y, 2)

def update():
    global cam_x, cam_y, cam_angle, speed

    # Steering
    if py16.btn('left'):  cam_angle -= TURN_RATE
    if py16.btn('right'): cam_angle += TURN_RATE

    # Acceleration / braking
    if py16.btn('up'):
        speed = min(MAX_SPEED, speed + ACCEL)
    elif py16.btn('down'):
        speed = max(-MAX_SPEED / 2, speed - BRAKE)
    else:
        # Coast: friction towards 0
        if speed > 0:
            speed = max(0, speed - FRICTION)
        else:
            speed = min(0, speed + FRICTION)

    # Move forward in the camera's facing direction
    cam_x += math.cos(cam_angle) * speed
    cam_y += math.sin(cam_angle) * speed

    # Horn
    if py16.btnp('z'):
        py16.tone(200, 200, py16.WAVE_SQUARE,
                  attack_ms=10, decay_ms=50, sustain=0.3, release_ms=80)

def draw():
    # Sky gradient: lighter blue toward horizon
    py16.cls(13)   # top: indigo
    py16.rectfill(0, 40, py16.WIDTH, 40, 12)   # middle: blue
    py16.rectfill(0, 70, py16.WIDTH, 10, 6)    # near horizon: light grey

    # Mode 7 ground plane below the horizon
    py16.mode7(cam_x, cam_y, cam_angle,
               horizon_y=80,
               cam_height=30,
               focal_length=70,
               sky_color=None)   # we already drew the sky

    # Player car: just the sprite stuck to the screen
    py16.spr(4, py16.WIDTH // 2 - 8, py16.HEIGHT - 32, w=2, h=1)

    # HUD
    py16.rectfill(0, 0, py16.WIDTH, 12, 0)
    py16.text(f"SPEED {abs(speed):4.1f}", 4, 3, 11)
    py16.text(f"DEG {int(math.degrees(cam_angle) % 360):3d}",
              py16.WIDTH - 60, 3, 7)

if __name__ == "__main__":
    py16.run(update, draw, init)
