"""
py16.cart
=========
Cart format for saving and loading a complete game state
(sprite sheet, map, sprite flags) as JSON file with base64-encoded
Sheet.
"""

import os
import base64
import json
import pygame

from . import state
from .core import PALETTE, SHEET_SIZE

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ======================================================================
# SPEICHERN
# ======================================================================

def save_cart(filename="cart.p16"):
    """Saves sheet (256x256 indices), map and flags as JSON.
    If filename ends in .pdf, the PDF variant with manual
    is created (see cart_pdf.export_pdf)."""
    if filename.lower().endswith(".pdf"):
        from . import cart_pdf
        return cart_pdf.export_pdf(filename)
    return _save_cart_p16(filename)

def _save_cart_p16(filename):
    # If the code editor is active and has meaningful content,
    # sync current editor state to cart_code. An editor with only
    # an empty line (initial default) does NOT overwrite cart_code.
    if hasattr(state, "ce_lines") and state.ce_lines:
        from . import code_editor
        cur_text = code_editor._lines_to_text(state.ce_lines)
        # Only sync if the editor content is more substantial than
        # the default-empty state (more than 1 line or real content)
        if len(state.ce_lines) > 1 or len(cur_text.strip()) > 0:
            state.cart_code = cur_text

    color_to_idx = {tuple(c): i for i, c in enumerate(PALETTE)}

    if _HAS_NUMPY:
        arr = pygame.surfarray.array3d(state.sprite_sheet)        # (W, H, 3)
        flat = arr.transpose(1, 0, 2).reshape(-1, 3)
        pal_arr = np.array(PALETTE, dtype=np.int32)
        diff = flat[:, None, :].astype(np.int32) - pal_arr[None, :, :]
        idx = (diff * diff).sum(-1).argmin(-1).astype(np.uint8)
        sheet_bytes = idx.tobytes()
    else:
        sheet_bytes = bytearray(SHEET_SIZE * SHEET_SIZE)
        for y in range(SHEET_SIZE):
            for x in range(SHEET_SIZE):
                rgb = tuple(state.sprite_sheet.get_at((x, y))[:3])
                sheet_bytes[y * SHEET_SIZE + x] = color_to_idx.get(rgb, 0)
        sheet_bytes = bytes(sheet_bytes)

    cart = {
        "version":   3,
        "engine":    "py-16",
        "width":     SHEET_SIZE,
        "height":    SHEET_SIZE,
        "sheet":     base64.b64encode(sheet_bytes).decode("ascii"),
        "map":       state.map_data,
        "flags":     state.sprite_flags,
        "sfx":       getattr(state, "sfx_patches", []),
        "patterns":  getattr(state, "music_patterns", []),
        "tracks":    getattr(state, "music_tracks", []),
        "code":      getattr(state, "cart_code", ""),
        "code_file": getattr(state, "cart_code_file", None),
        "meta":      getattr(state, "cart_meta", {}) or {},
    }
    with open(filename, "w") as f:
        json.dump(cart, f)
    print(f"Cart saved: {filename}")

# ======================================================================
# LADEN
# ======================================================================

def load_cart(filename="cart.p16"):
    """Loads cart from JSON file. For .pdf, the embedded
    cart attachment is extracted (see cart_pdf.load_pdf)."""
    if filename.lower().endswith(".pdf"):
        from . import cart_pdf
        return cart_pdf.load_pdf(filename)
    return _load_cart_p16(filename)

def _load_cart_p16(filename):
    if not os.path.exists(filename):
        print(f"Cart '{filename}' not found")
        return False
    with open(filename, "r") as f:
        cart = json.load(f)

    sheet_bytes = base64.b64decode(cart["sheet"])
    if _HAS_NUMPY:
        arr_idx = np.frombuffer(sheet_bytes, dtype=np.uint8)
        arr_idx = arr_idx.reshape(SHEET_SIZE, SHEET_SIZE)
        pal_arr = np.array(PALETTE, dtype=np.uint8)
        rgb = pal_arr[arr_idx].transpose(1, 0, 2)
        full = pygame.surfarray.array3d(state.sprite_sheet)
        full[:] = rgb
        pygame.surfarray.blit_array(state.sprite_sheet, full)
    else:
        for y in range(SHEET_SIZE):
            for x in range(SHEET_SIZE):
                idx = sheet_bytes[y * SHEET_SIZE + x]
                state.sprite_sheet.set_at((x, y), PALETTE[idx])

    state.map_data[:]     = cart["map"]
    state.sprite_flags[:] = cart["flags"]

    # SFX/Music load, if available (rueckwaertskompatibel mit v1)
    if "sfx" in cart and hasattr(state, "sfx_patches"):
        loaded_sfx = cart["sfx"]
        for i, p in enumerate(loaded_sfx):
            if i >= len(state.sfx_patches):
                break
            # JSON wandelt Tuples in Listen - backwandeln
            p["notes"] = [tuple(n) for n in p["notes"]]
            # ADSR/PWM defaults for old carts (before v1.0 ADSR update)
            p.setdefault("attack_ms",   0)
            p.setdefault("decay_ms",    0)
            p.setdefault("sustain",     1.0)
            p.setdefault("release_ms",  0)
            p.setdefault("pulse_width", 0.5)
            state.sfx_patches[i] = p
    if "patterns" in cart and hasattr(state, "music_patterns"):
        for i, p in enumerate(cart["patterns"]):
            if i >= len(state.music_patterns):
                break
            state.music_patterns[i] = p
    if "tracks" in cart and hasattr(state, "music_tracks"):
        for i, t in enumerate(cart["tracks"]):
            if i >= len(state.music_tracks):
                break
            state.music_tracks[i] = list(t)

    # Code-Felder load (rueckwaertskompatibel mit v1/v2)
    if "code" in cart:
        state.cart_code = cart["code"]
    if "code_file" in cart:
        state.cart_code_file = cart["code_file"]
    if "meta" in cart:
        state.cart_meta = cart["meta"] or {}
    # Wenn Code-Editor schon mal aktiv war: Lines-Buffer refresh
    if hasattr(state, "ce_lines"):
        from . import code_editor
        state.ce_lines = code_editor._text_to_lines(state.cart_code)
        state.ce_cur_row = 0
        state.ce_cur_col = 0
        state.ce_dirty = False

    print(f"Cart loaded: {filename}")
    return True
