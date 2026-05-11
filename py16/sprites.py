"""
py16.sprites
============
Sprite-Sheet: Pixel-Setzen, Sprite-Zeichnen mit Flip/Multi-Cel,
Bildfile-Quantisierung mit numpy-Beschleunigung.
"""

import os
import pygame

from . import state
from .core import (PALETTE, SHEET_SIZE, SPRITES_PER_ROW, SPRITE_PIX)

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ======================================================================
# PIXELZUGRIFF
# ======================================================================

def sset(x, y, color_index):
    if 0 <= x < SHEET_SIZE and 0 <= y < SHEET_SIZE:
        state.sprite_sheet.set_at((int(x), int(y)),
                                  PALETTE[color_index & 0xFF])

def sget(x, y):
    """Paletten-Index am Sheet-Pixel (Naehe)."""
    if 0 <= x < SHEET_SIZE and 0 <= y < SHEET_SIZE:
        r, g, b = state.sprite_sheet.get_at((int(x), int(y)))[:3]
        best, bd = 0, 1 << 30
        for i, (pr, pg, pb) in enumerate(PALETTE):
            d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
            if d < bd:
                bd, best = d, i
        return best
    return 0

# ======================================================================
# SPRITE ZEICHNEN
# ======================================================================

def spr(sprite_id, x, y, w=1, h=1, flip_x=False, flip_y=False):
    """Zeichnet Sprite (0-1023). w/h in 8x8-Cels. flip_x/y spiegelt."""
    sprite_id = int(sprite_id) % 1024
    sx = (sprite_id % SPRITES_PER_ROW) * SPRITE_PIX
    sy = (sprite_id // SPRITES_PER_ROW) * SPRITE_PIX
    pw, ph = int(w) * SPRITE_PIX, int(h) * SPRITE_PIX

    pw = min(pw, SHEET_SIZE - sx)
    ph = min(ph, SHEET_SIZE - sy)
    if pw <= 0 or ph <= 0:
        return

    src = state.sprite_sheet.subsurface((sx, sy, pw, ph))
    if flip_x or flip_y:
        src = pygame.transform.flip(src, flip_x, flip_y)

    m = getattr(state, "blend_mode", "normal")
    dest = (x - state.cam_x, y - state.cam_y)
    if m == "normal":
        state.screen.blit(src, dest)
    elif m == "alpha":
        # Need a copy because set_alpha modifies the surface globally
        tmp = src.copy()
        tmp.set_alpha(state.blend_alpha)
        state.screen.blit(tmp, dest)
    else:
        from .graphics import _blend_flag
        state.screen.blit(src, dest, special_flags=_blend_flag())

# ======================================================================
# BILDLADUNG MIT FARBQUANTISIERUNG
# ======================================================================

def load_spritesheet(filename):
    """Loads PNG/Bild und quantisiert auf die current Palette."""
    if not os.path.exists(filename):
        print(f"WARNUNG: Bild '{filename}' not found!")
        return
    try:
        img = pygame.image.load(filename).convert()
        if _HAS_NUMPY:
            _load_numpy(img)
        else:
            _load_python(img)
    except Exception as e:
        print(f"Fehler beim Bildload: {e}")

def _load_numpy(img):
    w = min(SHEET_SIZE, img.get_width())
    h = min(SHEET_SIZE, img.get_height())
    arr = pygame.surfarray.array3d(img)[:w, :h].astype(np.int32)
    pal = np.array(PALETTE, dtype=np.int32)
    diff = arr[..., None, :] - pal[None, None, :, :]
    dist = (diff * diff).sum(-1)
    idx = d.argmin(-1)
    new_colors = pal[idx].astype(np.uint8)
    full = pygame.surfarray.array3d(state.sprite_sheet)
    full[:w, :h] = new_colors
    pygame.surfarray.blit_array(state.sprite_sheet, full)

def _load_python(img):
    for y in range(min(SHEET_SIZE, img.get_height())):
        for x in range(min(SHEET_SIZE, img.get_width())):
            r, g, b = img.get_at((x, y))[:3]
            best, bd = 0, 1 << 30
            for i, (pr, pg, pb) in enumerate(PALETTE):
                d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
                if d < bd:
                    bd, best = d, i
            sset(x, y, best)
