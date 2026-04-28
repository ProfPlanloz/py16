"""
py16.maps
=========
Tile-Map (128x128) und Sprite-Flags. Unterstuetzt Layer-Filtering ueber
Sprite-Flags fuer Multi-Layer-Rendering.
"""

from . import state
from .core import MAP_W, MAP_H, WIDTH, HEIGHT
from .sprites import spr

# ======================================================================
# MAP
# ======================================================================

def mset(cel_x, cel_y, sprite_id):
    if 0 <= cel_x < MAP_W and 0 <= cel_y < MAP_H:
        state.map_data[int(cel_y)][int(cel_x)] = int(sprite_id) & 0x3FF

def mget(cel_x, cel_y):
    if 0 <= cel_x < MAP_W and 0 <= cel_y < MAP_H:
        return state.map_data[int(cel_y)][int(cel_x)]
    return 0

def draw_map(cel_x, cel_y, sx, sy, cel_w, cel_h, layer_flag=-1):
    """Zeichnet einen Map-Bereich.
    layer_flag (0..7): zeigt nur Sprites mit gesetztem Flag.
    layer_flag = -1: alle nicht-leeren Sprites."""
    for cy in range(cel_h):
        screen_y = sy + cy * 8 - state.cam_y
        if screen_y <= -8 or screen_y >= HEIGHT:
            continue
        my = cy + cel_y
        if my < 0 or my >= MAP_H:
            continue
        row = state.map_data[my]
        for cx in range(cel_w):
            screen_x = sx + cx * 8 - state.cam_x
            if screen_x <= -8 or screen_x >= WIDTH:
                continue
            mx = cx + cel_x
            if mx < 0 or mx >= MAP_W:
                continue
            sid = row[mx]
            if sid <= 0:
                continue
            if layer_flag >= 0 and not (state.sprite_flags[sid] & (1 << layer_flag)):
                continue
            spr(sid, sx + cx * 8, sy + cy * 8)

# ======================================================================
# SPRITE-FLAGS (8 Bit pro Sprite)
# ======================================================================

def fset(sprite_id, flag_index, value=True):
    sprite_id = int(sprite_id) % 1024
    if 0 <= flag_index <= 7:
        if value:
            state.sprite_flags[sprite_id] |= (1 << flag_index)
        else:
            state.sprite_flags[sprite_id] &= ~(1 << flag_index)

def fget(sprite_id, flag_index=None):
    """Ohne flag_index: liefert das gesamte Flag-Byte."""
    sprite_id = int(sprite_id) % 1024
    if flag_index is None:
        return state.sprite_flags[sprite_id]
    if 0 <= flag_index <= 7:
        return bool(state.sprite_flags[sprite_id] & (1 << flag_index))
    return False
