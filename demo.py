"""
py-16 demo game
================
Shows: 256-color palette, sprite flipping, multi-layer map,
parallax background, all 4 sound waveforms.

Keys:
    Arrows          : move
    Z / X / Space   : play Triangle / Saw / Noise
    F1              : Sprite editor
    F2              : Map editor
    F5              : save cart
    F8              : load cart
    ESC             : back / quit
"""

# @manual
# @description
# A small demo of the py-16 fantasy console.
# Steer a character through a parallax world with mountains
# in the background and a stone-tile landscape.
#
# @controls
# Arrows left/right : Move
# Z                   : Triangle sound
# X                   : Saw sound
# Space               : Noise sound
# F1                  : Sprite editor
# F6                  : Code editor
# F9                  : reload code
#
# @credits
# Engine and demo: py-16 user
# @end

import py16

# Zustand
px, py = 60.0, 100.0
pdir   = 1   # 1 = rechts, -1 = links

def init():
    # Editor mit dieser file verbinden, damit F6 den Live-Code zeigt.
    # Nur wenn __file__ existiert (also nicht aus einem Cart-Reload):
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

    # Sprite 1: gameerfigur (Pixel 8..15, 0..7)
    body = [
        "00111100",
        "01777710",
        "17787781",
        "17888881",
        "17888881",
        "01788810",
        "00188100",
        "00111100",
    ]
    for j, row in enumerate(body):
        for i, c in enumerate(row):
            if c != '0':
                py16.sset(8 + i, j, int(c))

    # Sprite 2: Bodenkachel (Pixel 16..23, 0..7) - Hintergrund-Layer
    for j in range(8):
        for i in range(8):
            col = 11 if j < 2 else 3
            if j < 2 and (i + j) % 3 == 0:
                col = 7
            py16.sset(16 + i, j, col)

    # Sprite 3: Stone (pixels 24..31, 0..7) - solid foreground layer
    for j in range(8):
        for i in range(8):
            col = 5 if (i + j) % 2 == 0 else 6
            py16.sset(24 + i, j, col)

    # Flags
    py16.fset(2, 0, True)   # Layer 0 = BG
    py16.fset(3, 1, True)   # Layer 1 = solid

    # Map fuellen
    for x in range(py16.MAP_W):
        py16.mset(x, 14, 2)
        if x % 7 == 3:
            py16.mset(x, 13, 3)
    for y in range(13, 18):
        py16.mset(20, y, 3)
        py16.mset(40, y, 3)

def update():
    global px, py, pdir
    if py16.btn('left'):
        px -= 1.5
        pdir = -1
    if py16.btn('right'):
        px += 1.5
        pdir = 1
    if py16.btnp('z'):
        py16.tone(440, 80, py16.WAVE_TRIANGLE)
    if py16.btnp('x'):
        py16.tone(220, 200, py16.WAVE_SAW)
    if py16.btnp('space'):
        py16.tone(80, 150, py16.WAVE_NOISE)

    py16.camera(int(px) - py16.WIDTH // 2, 0)

def draw():
    py16.cls(12)  # Himmelblau

    # Parallax: Berge mit halbierter Kamera-Geschwindigkeit
    py16.camera(int(px) // 2 - py16.WIDTH // 2, 0)
    for i in range(0, py16.MAP_W * 8, 40):
        py16.circfill(i, 130, 24, 13)
        py16.circfill(i + 20, 130, 18, 5)

    py16.camera(int(px) - py16.WIDTH // 2, 0)
    py16.draw_map(0, 0, 0, 0, py16.MAP_W, py16.MAP_H, layer_flag=0)
    py16.draw_map(0, 0, 0, 0, py16.MAP_W, py16.MAP_H, layer_flag=1)

    py16.spr(1, int(px), int(py), 1, 1, flip_x=(pdir < 0))

    # HUD ohne Kamera
    py16.camera(0, 0)
    py16.text(f"PY-16 ENGINE   FPS:{int(py16.fps())}", 4, 4, 7)
    py16.text(f"FRAME:{py16.t()}", 4, 12, 6)
    py16.text("PFEILE BEWEGEN  Z X SPACE FUER SOUND",
              4, py16.HEIGHT - 18, 7)
    py16.text("F1 SPR  F2 MAP  F5 SAVE  F8 LOAD",
              4, py16.HEIGHT - 10, 6)

if __name__ == "__main__":
    py16.run(update, draw, init)
