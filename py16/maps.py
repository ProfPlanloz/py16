"""
py16.maps
=========
Tile maps (128x128) on up to 4 layers, plus sprite flags.

Layer 0 is the default (the original `state.map_data`). Layers 1..3
live in `state.map_layers`. All map functions accept an optional
`layer=0..3` parameter; passing nothing keeps the old behavior.

Render order is up to the cart: typically draw_map(layer=0) first
(background), then sprites/entities, then draw_map(layer=2) on top
(foreground vegetation), and so on.
"""

from . import state
from .core import MAP_W, MAP_H, WIDTH, HEIGHT
from .sprites import spr

NUM_LAYERS = 4

# ======================================================================
# LAYER ACCESS
# ======================================================================

def _get_layer_data(layer):
    """Returns the 2D map array for the given layer (0..3).
    Layer 0 is state.map_data (back-compat); 1..3 are in state.map_layers."""
    if layer == 0:
        return state.map_data
    if 1 <= layer <= NUM_LAYERS - 1:
        idx = layer - 1
        if not hasattr(state, "map_layers") or state.map_layers is None:
            state.map_layers = [
                [[0] * MAP_W for _ in range(MAP_H)] for _ in range(NUM_LAYERS - 1)
            ]
        while idx >= len(state.map_layers):
            state.map_layers.append([[0] * MAP_W for _ in range(MAP_H)])
        return state.map_layers[idx]
    return None

# ======================================================================
# MAP
# ======================================================================

def mset(cel_x, cel_y, sprite_id, layer=0):
    """Set a tile at (cel_x, cel_y) on the given layer (0..3)."""
    data = _get_layer_data(layer)
    if data is None:
        return
    if 0 <= cel_x < MAP_W and 0 <= cel_y < MAP_H:
        data[int(cel_y)][int(cel_x)] = int(sprite_id) & 0x3FF

def mget(cel_x, cel_y, layer=0):
    """Get the tile at (cel_x, cel_y) on the given layer."""
    data = _get_layer_data(layer)
    if data is None:
        return 0
    if 0 <= cel_x < MAP_W and 0 <= cel_y < MAP_H:
        return data[int(cel_y)][int(cel_x)]
    return 0

def mclear(layer=0):
    """Clear the entire layer to 0."""
    data = _get_layer_data(layer)
    if data is None:
        return
    for row in data:
        for i in range(len(row)):
            row[i] = 0

def draw_map(cel_x, cel_y, sx, sy, cel_w, cel_h, layer_flag=-1, layer=0):
    """Draws a map region from the given layer.

    layer       : map layer 0..3 to render (default 0)
    layer_flag  : sprite flag filter (-1 = all, 0..7 = only sprites
                  whose flag at that bit is set)
    """
    data = _get_layer_data(layer)
    if data is None:
        return
    for cy in range(cel_h):
        screen_y = sy + cy * 8 - state.cam_y
        if screen_y <= -8 or screen_y >= HEIGHT:
            continue
        my = cy + cel_y
        if my < 0 or my >= MAP_H:
            continue
        row = data[my]
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
# SPRITE FLAGS (8 bits per sprite)
# ======================================================================

def fset(sprite_id, flag_index, value=True):
    sprite_id = int(sprite_id) % 1024
    if 0 <= flag_index <= 7:
        if value:
            state.sprite_flags[sprite_id] |= (1 << flag_index)
        else:
            state.sprite_flags[sprite_id] &= ~(1 << flag_index)

def fget(sprite_id, flag_index=None):
    """Without flag_index: returns the full flag byte."""
    sprite_id = int(sprite_id) % 1024
    if flag_index is None:
        return state.sprite_flags[sprite_id]
    if 0 <= flag_index <= 7:
        return bool(state.sprite_flags[sprite_id] & (1 << flag_index))
    return False
