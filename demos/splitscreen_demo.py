"""
SPLITSCREEN DEMO for py-16
===========================

Two players explore the same big world. Each gets their own
camera-tracked viewport. A shared HUD shows both scores on top.

# @manual
# @description
# 2-player splitscreen exploration. Both players are on the same big
# tile world but can move independently. Collect coins (yellow tiles)
# for points. First to 10 wins.
#
# @controls
# P1   : Arrow keys OR gamepad 1
# P2   : W/A/S/D OR gamepad 2
# Z    : Reset (any player)
# F12  : Back to BIOS
#
# @credits
# py-16 demo cart
# @end
"""

import math
import py16

# World size (in tiles, 8 px each)
MAP_W = 64
MAP_H = 64

# Player state
players = [
    {"x": 80.0,  "y": 80.0, "score": 0},
    {"x": 400.0, "y": 200.0, "score": 0},
]

WIN_SCORE = 10
game_over = False
winner = -1

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass

    # Sprite 1: grass tile
    grass = [
        "33333333",
        "32333333",
        "33333333",
        "33333133",
        "33333333",
        "33323333",
        "33333333",
        "33333333",
    ]
    _paint_sprite(1, grass)

    # Sprite 2: stone/wall tile
    stone = [
        "55555555",
        "56555655",
        "55556555",
        "55555555",
        "55565556",
        "55555555",
        "56555555",
        "55555555",
    ]
    _paint_sprite(2, stone)

    # Sprite 3: coin (yellow with sparkle)
    coin = [
        "00099000",
        "09a9a900",
        "0a99a900",
        "0a99a900",
        "09a9a900",
        "00999000",
        "00000000",
        "00000000",
    ]
    _paint_sprite(3, coin)

    # Sprite 4: P1 (red character)
    p1 = [
        "00777700",
        "07788770",
        "07788770",
        "77777777",
        "08888880",
        "08888880",
        "00800800",
        "00800800",
    ]
    _paint_sprite(4, p1)

    # Sprite 5: P2 (blue character)
    p2 = [
        "00777700",
        "0bccbb70",
        "07ccbb70",
        "77bbbb77",
        "0cccccc0",
        "0cccccc0",
        "00c00c00",
        "00c00c00",
    ]
    _paint_sprite(5, p2)

    # Build the map: grass everywhere, walls on the borders, scattered coins
    for y in range(MAP_H):
        for x in range(MAP_W):
            if x == 0 or x == MAP_W - 1 or y == 0 or y == MAP_H - 1:
                py16.mset(x, y, 2)         # wall
            else:
                py16.mset(x, y, 1)         # grass

    # Some internal walls
    for y in range(20, 28):
        py16.mset(30, y, 2)
    for x in range(40, 50):
        py16.mset(x, 40, 2)

    # Coins scattered around (use seeded random for reproducibility)
    import random
    random.seed(1)
    for _ in range(20):
        x = random.randint(2, MAP_W - 3)
        y = random.randint(2, MAP_H - 3)
        if py16.mget(x, y) == 1:
            py16.mset(x, y, 3)             # coin

def _paint_sprite(sprite_id, rows):
    sx = (sprite_id % 32) * 8
    sy = (sprite_id // 32) * 8
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            try:
                v = int(c, 16)
            except ValueError:
                v = 0
            py16.sset(sx + i, sy + j, v)

def _move_player(p, dx, dy):
    """Move player, respecting walls."""
    nx = p["x"] + dx
    ny = p["y"] + dy
    # Check tile at new position
    tx = int(nx) // 8
    ty = int(ny) // 8
    if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
        tile = py16.mget(tx, ty)
        if tile == 2:
            return                          # wall, block
        if tile == 3:
            # Coin!
            py16.mset(tx, ty, 1)            # remove coin
            p["score"] += 1
            py16.tone(800, 80, py16.WAVE_TRIANGLE,
                      attack_ms=5, decay_ms=40, release_ms=80)
    p["x"] = max(8, min(MAP_W * 8 - 8, nx))
    p["y"] = max(8, min(MAP_H * 8 - 8, ny))

def update():
    global game_over, winner

    if game_over:
        if py16.btnp('z') or py16.btnp('z', player=2):
            _reset()
        return

    speed = 1.5

    # P1: arrow keys OR gamepad 1
    if py16.btn('left',  player=1): _move_player(players[0], -speed, 0)
    if py16.btn('right', player=1): _move_player(players[0],  speed, 0)
    if py16.btn('up',    player=1): _move_player(players[0], 0, -speed)
    if py16.btn('down',  player=1): _move_player(players[0], 0,  speed)

    # P2: WASD (always available) OR gamepad 2
    if py16.player_connected(2):
        if py16.btn('left',  player=2): _move_player(players[1], -speed, 0)
        if py16.btn('right', player=2): _move_player(players[1],  speed, 0)
        if py16.btn('up',    player=2): _move_player(players[1], 0, -speed)
        if py16.btn('down',  player=2): _move_player(players[1], 0,  speed)
    else:
        # Keyboard split for P2: WASD
        if py16.btn('a'): _move_player(players[1], -speed, 0)
        if py16.btn('d'): _move_player(players[1],  speed, 0)
        if py16.btn('w'): _move_player(players[1], 0, -speed)
        if py16.btn('s'): _move_player(players[1], 0,  speed)

    # Win condition
    for i, p in enumerate(players):
        if p["score"] >= WIN_SCORE:
            game_over = True
            winner = i + 1
            py16.tone(440, 200, py16.WAVE_TRIANGLE,
                      attack_ms=20, decay_ms=100, release_ms=200)

def _reset():
    global game_over, winner
    players[0]["x"] = 80.0
    players[0]["y"] = 80.0
    players[0]["score"] = 0
    players[1]["x"] = 400.0
    players[1]["y"] = 200.0
    players[1]["score"] = 0
    game_over = False
    winner = -1
    init()    # restore coins

def _draw_world_for(p_idx):
    """Draw the world from player p_idx's point of view inside the
    currently active viewport."""
    p = players[p_idx]
    # Get viewport size to center the camera
    rect = py16.viewport_rect()
    vw, vh = rect[2], rect[3]

    # Camera: center on player
    py16.camera(int(p["x"]) - vw // 2,
                int(p["y"]) - vh // 2)

    py16.cls(0)
    # Draw enough tiles to cover the viewport
    cam_tx = (int(p["x"]) - vw // 2) // 8
    cam_ty = (int(p["y"]) - vh // 2) // 8
    py16.draw_map(cam_tx, cam_ty,
                  cam_tx * 8, cam_ty * 8,
                  vw // 8 + 2, vh // 8 + 2)

    # Both players are visible in both viewports if they are in range
    for i, op in enumerate(players):
        sprite_id = 4 + i
        py16.spr(sprite_id, int(op["x"]) - 4, int(op["y"]) - 4)

def draw():
    # === SHARED LAYOUT: 2 viewports side by side ===
    py16.split_layout("horizontal")

    # Black background between viewports
    py16.viewport(0)
    py16.cls(0)

    # === Each player's view ===
    for p_idx in range(2):
        py16.viewport(p_idx + 1)
        _draw_world_for(p_idx)

    # Reset to full screen for shared overlay
    py16.viewport(0)

    # === Divider line ===
    py16.line(py16.WIDTH // 2, 0,
              py16.WIDTH // 2, py16.HEIGHT, 5)

    # === Per-viewport HUD (player label) ===
    py16.viewport(1)
    sx, sy = py16.viewport_local(4, 4)
    py16.text(f"P1 {players[0]['score']:02d}", sx, sy, 8)
    py16.viewport(2)
    sx, sy = py16.viewport_local(4, 4)
    py16.text(f"P2 {players[1]['score']:02d}", sx, sy, 12)

    # === Shared HUD bottom: status / win banner ===
    py16.viewport(0)
    py16.rectfill(0, py16.HEIGHT - 10, py16.WIDTH, 10, 0)
    if game_over:
        msg = f"P{winner} WINS! Z TO RESTART"
        py16.text(msg, py16.WIDTH // 2 - len(msg) * 2,
                  py16.HEIGHT - 8, 11)
    else:
        py16.text(f"FIRST TO {WIN_SCORE} COINS WINS",
                  py16.WIDTH // 2 - 50, py16.HEIGHT - 8, 6)

if __name__ == "__main__":
    py16.run(update, draw, init)
