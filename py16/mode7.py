"""
py16.mode7
===========
Mode 7-style affine map rendering. Projects the tile map onto a
perspective ground plane, like Super Mario Kart or F-Zero.

Usage:
    py16.mode7(cam_x, cam_y, angle, horizon_y=64,
               cam_height=32.0, focal_length=64.0,
               sky_color=None)

Parameters:
    cam_x, cam_y   Camera position in pixel coordinates (map space).
                   cam_x=0, cam_y=0 means the camera is at the top-left
                   tile of the map.
    angle          Camera rotation in radians. 0 looks toward +X (right).
    horizon_y      Screen Y of the horizon line. Pixels above are not
                   touched (the cart can draw a sky there). Default 64.
    cam_height     How high above the ground the camera sits. Larger
                   values look down more steeply. Default 32.
    focal_length   Lens focal length, controls field of view. Smaller
                   = wider FOV (more perspective distortion). Default 64.
    sky_color      If given (palette index), fills above the horizon
                   with this color. None = leaves what's already there.

The map can be 0..MAP_W-1 tiles wide; sampling outside wraps (so the
ground tiles tile infinitely, classic Mode 7 look).
"""

import math
import pygame

from . import state
from .core import WIDTH, HEIGHT, MAP_W, MAP_H, PALETTE

try:
    import numpy as _np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

TILE_SIZE = 8

def mode7(cam_x, cam_y, angle,
          horizon_y=64,
          cam_height=32.0,
          focal_length=64.0,
          sky_color=None,
          scanline_angles=None,
          scanline_offsets_x=None,
          scanline_offsets_y=None,
          layer=0):
    """Render a tile map layer as a Mode-7-style perspective ground plane.

    Standard parameters (cam_x, cam_y, angle, etc.) work as before.

    layer : which map layer (0..3) to use as the ground texture.
            Default 0 (the main map). Useful for switching between
            ground textures in different game modes.

    Per-scanline effects:
        scanline_angles    : list/array of length n_rows. Each value is
                             ADDED to the base angle for that scanline.
                             Used for wave / tunnel / shake effects.
        scanline_offsets_x : list/array of length n_rows. Added to cam_x
                             for that scanline. Used for earthquake /
                             heat-mirage effects.
        scanline_offsets_y : same, for cam_y.

    n_rows = HEIGHT - horizon_y. Helper functions like mode7_wave() and
    mode7_earthquake() build these arrays for common effects.

    See module docstring for full parameter details."""
    if state.screen is None or state.sprite_sheet is None:
        return

    if sky_color is not None:
        from .graphics import rectfill
        rectfill(0, 0, WIDTH, max(0, horizon_y), sky_color)

    if horizon_y >= HEIGHT:
        return

    if _HAS_NUMPY:
        _render_numpy(cam_x, cam_y, angle, horizon_y,
                      cam_height, focal_length,
                      scanline_angles,
                      scanline_offsets_x,
                      scanline_offsets_y,
                      layer)
    else:
        _render_python(cam_x, cam_y, angle, horizon_y,
                       cam_height, focal_length,
                       scanline_angles,
                       scanline_offsets_x,
                       scanline_offsets_y,
                       layer)

# ----------------------------------------------------------------------
# NUMPY-BASED FAST PATH (60+ FPS even on Pi)
# ----------------------------------------------------------------------

# Cache: a numpy lookup table mapping (sprite_id, sx, sy) to RGB.
# We rebuild it from the sprite sheet when needed.
_sheet_array_cache = None
_sheet_array_id    = None   # tracks a counter on state.sprite_sheet

def _build_sheet_array():
    """Convert the sprite sheet to a numpy RGB array (H, W, 3)."""
    surf = state.sprite_sheet
    arr = pygame.surfarray.array3d(surf)        # shape (W, H, 3)
    arr = arr.transpose(1, 0, 2)                # shape (H, W, 3)
    return arr

def _build_map_tile_array(layer=0):
    """Convert the given map layer to a numpy array (MAP_H, MAP_W) of tile IDs."""
    from .maps import _get_layer_data
    data = _get_layer_data(layer)
    if data is None:
        return _np.zeros((MAP_H, MAP_W), dtype=_np.int16)
    return _np.asarray(data, dtype=_np.int16)

def _render_numpy(cam_x, cam_y, angle, horizon_y,
                  cam_height, focal_length,
                  scanline_angles=None,
                  scanline_offsets_x=None,
                  scanline_offsets_y=None,
                  layer=0):
    sheet = _build_sheet_array()
    map_arr = _build_map_tile_array(layer)

    sheet_h, sheet_w, _ = sheet.shape
    sprites_per_row = sheet_w // TILE_SIZE

    n_rows = HEIGHT - horizon_y

    # Per-row distance
    y_from_horizon = _np.arange(1, n_rows + 1, dtype=_np.float32)
    distance = (cam_height * focal_length) / y_from_horizon

    # Per-row angle: base + optional per-scanline offset
    if scanline_angles is not None:
        sa = _np.asarray(scanline_angles, dtype=_np.float32)
        # Pad/truncate to exactly n_rows
        if len(sa) < n_rows:
            sa = _np.concatenate([sa, _np.zeros(n_rows - len(sa), dtype=_np.float32)])
        elif len(sa) > n_rows:
            sa = sa[:n_rows]
        per_row_angle = angle + sa
    else:
        per_row_angle = _np.full(n_rows, angle, dtype=_np.float32)

    cos_a = _np.cos(per_row_angle)        # (n_rows,)
    sin_a = _np.sin(per_row_angle)

    # Per-row camera position with optional per-scanline offset
    base_cx = float(cam_x)
    base_cy = float(cam_y)
    if scanline_offsets_x is not None:
        sox = _np.asarray(scanline_offsets_x, dtype=_np.float32)
        if len(sox) < n_rows:
            sox = _np.concatenate([sox, _np.zeros(n_rows - len(sox), dtype=_np.float32)])
        elif len(sox) > n_rows:
            sox = sox[:n_rows]
        per_row_cx = base_cx + sox
    else:
        per_row_cx = _np.full(n_rows, base_cx, dtype=_np.float32)

    if scanline_offsets_y is not None:
        soy = _np.asarray(scanline_offsets_y, dtype=_np.float32)
        if len(soy) < n_rows:
            soy = _np.concatenate([soy, _np.zeros(n_rows - len(soy), dtype=_np.float32)])
        elif len(soy) > n_rows:
            soy = soy[:n_rows]
        per_row_cy = base_cy + soy
    else:
        per_row_cy = _np.full(n_rows, base_cy, dtype=_np.float32)

    # Center-of-row map coords: cam + distance * (cos, sin)
    center_x = per_row_cx + distance * cos_a
    center_y = per_row_cy + distance * sin_a

    # Per-row "step" in map coords for moving 1 pixel right on screen
    step_factor = distance / focal_length
    step_x = -sin_a * step_factor
    step_y =  cos_a * step_factor

    px_offset = _np.arange(WIDTH, dtype=_np.float32) - (WIDTH / 2)

    # Map coords for every (row, col)
    map_x = center_x[:, None] + px_offset[None, :] * step_x[:, None]
    map_y = center_y[:, None] + px_offset[None, :] * step_y[:, None]

    # Wrap around so the world tiles
    map_w_px = MAP_W * TILE_SIZE
    map_h_px = MAP_H * TILE_SIZE
    map_x = _np.mod(map_x, map_w_px).astype(_np.int32)
    map_y = _np.mod(map_y, map_h_px).astype(_np.int32)

    tile_x = map_x // TILE_SIZE
    tile_y = map_y // TILE_SIZE
    in_tile_x = map_x % TILE_SIZE
    in_tile_y = map_y % TILE_SIZE

    tile_ids = map_arr[tile_y, tile_x]

    sheet_x = (tile_ids % sprites_per_row) * TILE_SIZE + in_tile_x
    sheet_y = (tile_ids // sprites_per_row) * TILE_SIZE + in_tile_y

    sheet_x = _np.clip(sheet_x, 0, sheet_w - 1)
    sheet_y = _np.clip(sheet_y, 0, sheet_h - 1)

    sampled = sheet[sheet_y, sheet_x]

    target = pygame.Surface((WIDTH, n_rows))
    arr_t = sampled.transpose(1, 0, 2)
    pygame.surfarray.blit_array(target, arr_t)
    state.screen.blit(target, (0, horizon_y))

# ----------------------------------------------------------------------
# PYTHON FALLBACK (for when numpy isn't installed)
# ----------------------------------------------------------------------

def _render_python(cam_x, cam_y, angle, horizon_y,
                   cam_height, focal_length,
                   scanline_angles=None,
                   scanline_offsets_x=None,
                   scanline_offsets_y=None,
                   layer=0):
    """Slow fallback. Renders one row at a time without numpy.
    Use a coarser pixel step (every 2nd pixel) to stay roughly playable."""
    from .maps import _get_layer_data
    map_data = _get_layer_data(layer)
    if map_data is None:
        return
    sheet = state.sprite_sheet
    sheet_w, sheet_h = sheet.get_size()
    sprites_per_row = sheet_w // TILE_SIZE
    map_w_px = MAP_W * TILE_SIZE
    map_h_px = MAP_H * TILE_SIZE

    # Coarse step: 2x pixels per draw, helps fallback FPS
    step = 2
    out = pygame.Surface((WIDTH, 1))

    n_rows = HEIGHT - horizon_y

    for ridx, row in enumerate(range(horizon_y, HEIGHT)):
        y_from_horizon = ridx + 1
        distance = (cam_height * focal_length) / y_from_horizon

        # Per-row angle and offsets
        a = angle
        if scanline_angles is not None and ridx < len(scanline_angles):
            a += scanline_angles[ridx]
        cx = cam_x
        cy = cam_y
        if scanline_offsets_x is not None and ridx < len(scanline_offsets_x):
            cx += scanline_offsets_x[ridx]
        if scanline_offsets_y is not None and ridx < len(scanline_offsets_y):
            cy += scanline_offsets_y[ridx]

        cos_a = math.cos(a)
        sin_a = math.sin(a)
        center_x = cx + distance * cos_a
        center_y = cy + distance * sin_a
        sf = distance / focal_length
        sx = -sin_a * sf
        sy =  cos_a * sf

        for col in range(0, WIDTH, step):
            offs = col - WIDTH / 2
            mx = int((center_x + offs * sx) % map_w_px)
            my = int((center_y + offs * sy) % map_h_px)
            tx = mx // TILE_SIZE
            ty = my // TILE_SIZE
            ix = mx % TILE_SIZE
            iy = my % TILE_SIZE
            tile_id = map_data[ty][tx]
            sheet_x = (tile_id % sprites_per_row) * TILE_SIZE + ix
            sheet_y = (tile_id // sprites_per_row) * TILE_SIZE + iy
            try:
                color = sheet.get_at((sheet_x, sheet_y))
            except (IndexError, pygame.error):
                color = (0, 0, 0)
            for k in range(step):
                if col + k < WIDTH:
                    out.set_at((col + k, 0), color)
        state.screen.blit(out, (0, row))

# ----------------------------------------------------------------------
# SCANLINE-EFFECT HELPERS
# ----------------------------------------------------------------------
# These produce arrays suitable for the scanline_angles / scanline_offsets
# parameters of mode7(). All return a numpy array (or list as fallback)
# of length n_rows. n_rows = HEIGHT - horizon_y.

def mode7_wave(n_rows, time, amplitude=4.0, frequency=0.3, speed=2.0):
    """Horizontal wave shake -- the world wobbles left/right per scanline,
    like heat rising or a rocking boat. Returns scanline_offsets_x array.

    n_rows    : number of scanlines below horizon (HEIGHT - horizon_y)
    time      : current frame counter or any monotonic float
    amplitude : how many map pixels each row shifts at peak
    frequency : how dense the wave (higher = more ripples on screen)
    speed     : how fast the wave moves over time
    """
    if _HAS_NUMPY:
        idx = _np.arange(n_rows, dtype=_np.float32)
        return amplitude * _np.sin(idx * frequency + time * speed)
    return [amplitude * math.sin(i * frequency + time * speed)
            for i in range(n_rows)]

def mode7_earthquake(n_rows, time, amplitude=2.0, decay=True):
    """Random per-scanline shake on both X and Y. Use during boss-impact
    or screen-shake moments. Returns (offsets_x, offsets_y) tuple.

    decay : if True, shake amplitude is stronger nearer the horizon
            (creates a feeling of distant impact). Set False for uniform.
    """
    if _HAS_NUMPY:
        idx = _np.arange(n_rows, dtype=_np.float32)
        # Pseudo-random per-row offsets, time-varying
        ox = amplitude * _np.sin(idx * 1.7 + time * 7.0)
        oy = amplitude * _np.cos(idx * 2.3 + time * 5.0)
        if decay:
            # Stronger at top (horizon), weaker at bottom
            falloff = (n_rows - idx) / n_rows
            ox *= falloff
            oy *= falloff
        return ox, oy
    ox = []
    oy = []
    for i in range(n_rows):
        s = math.sin(i * 1.7 + time * 7.0) * amplitude
        c = math.cos(i * 2.3 + time * 5.0) * amplitude
        if decay:
            f = (n_rows - i) / n_rows
            s *= f; c *= f
        ox.append(s)
        oy.append(c)
    return ox, oy

def mode7_tunnel(n_rows, twist=0.5):
    """Per-scanline angle twist for a tunnel/wormhole effect. The world
    rotates more strongly near the horizon, less near the camera.

    twist : peak angle offset in radians at the horizon (e.g. 0.5 = ~28 deg)
    """
    if _HAS_NUMPY:
        idx = _np.arange(n_rows, dtype=_np.float32)
        # Larger twist at the top (small idx), 0 at the bottom (large idx)
        falloff = (n_rows - idx) / n_rows
        return twist * falloff
    return [twist * (n_rows - i) / n_rows for i in range(n_rows)]

def mode7_curve(n_rows, time, curvature=0.3, period=80.0):
    """Per-scanline angle that bends like a curving road. Use for racing
    games where the track snakes left-right ahead of the player.

    curvature : peak angle bend in radians
    period    : how slowly the curve sweeps over time
    """
    if _HAS_NUMPY:
        idx = _np.arange(n_rows, dtype=_np.float32)
        falloff = (n_rows - idx) / n_rows   # stronger at horizon
        return curvature * _np.sin(time / period) * falloff
    return [curvature * math.sin(time / period) * (n_rows - i) / n_rows
            for i in range(n_rows)]
