"""
PARALLAX DEMO for py-16
========================

Demonstrates multi-layer maps with classic SNES-style parallax.
Four map layers scroll at different speeds, giving a sense of depth:

  Layer 1 (BG far):    Mountains - very slow scroll (x*0.2)
  Layer 2 (BG mid):    Clouds    - slow scroll (x*0.5)
  Layer 3 (gameplay):  Ground    - 1:1 with player position
  Layer 4 (FG):        Grass     - 1:1, drawn on top of player

# @manual
# @description
# Side-scrolling parallax demo using all 4 map layers.
# Walk left/right with the arrow keys to see the layers move
# at different speeds.
#
# @controls
# Arrows : Walk left/right
# F12    : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import py16

cam_x = 0.0
player_x = 128
walk_frame = 0

# Sprite IDs
SP_MOUNTAIN = 1
SP_CLOUD    = 2
SP_GROUND   = 3
SP_GRASS    = 4
SP_PLAYER   = 5

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

    # --- Sprite 1: Mountain silhouette (8x8) ---
    mountain = [
        "00000000",
        "00007000",
        "00077700",
        "00777770",
        "07777777",
        "77777777",
        "77777777",
        "77777777",
    ]
    _paint_sprite(SP_MOUNTAIN, mountain)

    # --- Sprite 2: Cloud puff ---
    cloud = [
        "00077000",
        "00777700",
        "07777770",
        "77777777",
        "07777770",
        "00077000",
        "00000000",
        "00000000",
    ]
    _paint_sprite(SP_CLOUD, cloud)

    # --- Sprite 3: Ground tile (dark green dirt) ---
    ground = [
        "33333333",
        "33333333",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
    ]
    _paint_sprite(SP_GROUND, ground)

    # --- Sprite 4: Grass blades (foreground) ---
    grass = [
        "00000000",
        "00000000",
        "00000000",
        "00000000",
        "00033030",
        "30330330",
        "33333333",
        "33333333",
    ]
    _paint_sprite(SP_GRASS, grass)

    # --- Sprite 5: Player (simple character) ---
    player = [
        "00077700",
        "00077700",
        "00077700",
        "07788770",
        "77788777",
        "07788770",
        "00088000",
        "00808080",
    ]
    _paint_sprite(SP_PLAYER, player)

    # === Layer 0 (back): scattered mountains across all of map ===
    py16.mclear(layer=0)
    for x in range(0, 128, 6):
        # Mountains at random heights
        h = 4 + (x * 7 % 5)
        for y in range(20 - h, 20):
            py16.mset(x, y, SP_MOUNTAIN, layer=0)
            py16.mset(x + 1, y, SP_MOUNTAIN, layer=0)

    # === Layer 1 (mid): clouds drifting ===
    py16.mclear(layer=1)
    for x in range(2, 128, 9):
        y = 5 + (x * 13 % 7)
        py16.mset(x, y, SP_CLOUD, layer=1)
        py16.mset(x + 1, y, SP_CLOUD, layer=1)

    # === Layer 2 (gameplay): ground line ===
    py16.mclear(layer=2)
    for x in range(128):
        py16.mset(x, 24, SP_GROUND, layer=2)
        py16.mset(x, 25, SP_GROUND, layer=2)
        py16.mset(x, 26, SP_GROUND, layer=2)

    # === Layer 3 (foreground): tufts of grass ===
    py16.mclear(layer=3)
    for x in range(0, 128, 3):
        py16.mset(x, 23, SP_GRASS, layer=3)

def _paint_sprite(sprite_id, rows):
    """Paint an 8x8 sprite from a list of 8 strings of palette digits."""
    sx = (sprite_id % 32) * 8
    sy = (sprite_id // 32) * 8
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            py16.sset(sx + i, sy + j, int(c, 16) if c.isdigit() else 0)

def update():
    global cam_x, player_x, walk_frame

    if py16.btn('left'):
        player_x -= 1.5
        walk_frame += 1
    elif py16.btn('right'):
        player_x += 1.5
        walk_frame += 1
    else:
        walk_frame = 0

    # Camera follows player, but doesn't go negative
    cam_x = max(0, player_x - py16.WIDTH // 2)

def draw():
    py16.cls(13)   # purple-blue sky

    # === BG layer 0 (mountains): very slow parallax (0.2x) ===
    bg_offset = int(cam_x * 0.2)
    py16.draw_map(bg_offset // 8, 0, -(bg_offset % 8), 24,
                  py16.WIDTH // 8 + 2, 24, layer=0)

    # === BG layer 1 (clouds): slow parallax (0.5x) ===
    cloud_offset = int(cam_x * 0.5)
    py16.draw_map(cloud_offset // 8, 0, -(cloud_offset % 8), 0,
                  py16.WIDTH // 8 + 2, 24, layer=1)

    # === Gameplay layer 2 (ground): 1:1 ===
    ground_offset = int(cam_x)
    py16.draw_map(ground_offset // 8, 24, -(ground_offset % 8), 24*8,
                  py16.WIDTH // 8 + 2, 4, layer=2)

    # === Player sprite (between gameplay and foreground) ===
    bob = (walk_frame // 4) % 2
    py16.spr(SP_PLAYER, int(player_x - cam_x) - 4,
             py16.HEIGHT - 56 + bob)

    # === FG layer 3 (grass): 1:1, drawn on top ===
    grass_offset = int(cam_x)
    py16.draw_map(grass_offset // 8, 23, -(grass_offset % 8), 23*8,
                  py16.WIDTH // 8 + 2, 1, layer=3)

    # HUD
    py16.rectfill(0, 0, py16.WIDTH, 12, 0)
    py16.text("PARALLAX DEMO", 4, 3, 11)
    py16.text(f"X {int(player_x):04d}",
              py16.WIDTH - 50, 3, 7)
    py16.text("ARROWS WALK", 4, py16.HEIGHT - 8, 6)

if __name__ == "__main__":
    py16.run(update, draw, init)
