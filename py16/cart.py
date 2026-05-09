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
        "version":    3,
        "engine":     "py-16",
        "width":      SHEET_SIZE,
        "height":     SHEET_SIZE,
        "sheet":      base64.b64encode(sheet_bytes).decode("ascii"),
        "map":        state.map_data,
        "map_layers": _serialize_map_layers(),
        "flags":      state.sprite_flags,
        "sfx":        getattr(state, "sfx_patches", []),
        "patterns":   getattr(state, "music_patterns", []),
        "tracks":     getattr(state, "music_tracks", []),
        "samples":    _serialize_samples(),
        "code":       getattr(state, "cart_code", ""),
        "code_file":  getattr(state, "cart_code_file", None),
        "meta":       getattr(state, "cart_meta", {}) or {},
    }
    with open(filename, "w") as f:
        json.dump(cart, f)
    print(f"Cart saved: {filename}")

def _serialize_map_layers():
    """Returns the extra layers (1..3) for cart JSON. Empty layers
    are stored as None to keep the cart small if the cart only uses
    layer 0."""
    layers = getattr(state, "map_layers", None)
    if not layers:
        return []
    out = []
    for layer in layers:
        is_empty = all(all(v == 0 for v in row) for row in layer)
        out.append(None if is_empty else layer)
    return out

def _restore_map_layers(loaded):
    """Restore layers 1..3 from cart data. Each entry can be a 2D map
    array or None (=> blank layer). Missing entries also count as blank."""
    from .core import MAP_W, MAP_H
    from .maps import NUM_LAYERS
    n_extra = NUM_LAYERS - 1
    if not hasattr(state, "map_layers") or state.map_layers is None:
        state.map_layers = [
            [[0] * MAP_W for _ in range(MAP_H)] for _ in range(n_extra)
        ]
    for i in range(n_extra):
        if i < len(loaded) and loaded[i] is not None:
            state.map_layers[i] = loaded[i]
        else:
            # Reset to all zeros
            for row in state.map_layers[i]:
                for j in range(len(row)):
                    row[j] = 0

def _clear_extra_layers():
    """Reset layers 1..3 to all zero (used when loading an old cart
    without map_layers field)."""
    from .core import MAP_W, MAP_H
    from .maps import NUM_LAYERS
    n_extra = NUM_LAYERS - 1
    if not hasattr(state, "map_layers") or state.map_layers is None:
        state.map_layers = [
            [[0] * MAP_W for _ in range(MAP_H)] for _ in range(n_extra)
        ]
    else:
        for layer in state.map_layers:
            for row in layer:
                for j in range(len(row)):
                    row[j] = 0

def _serialize_samples():
    """Returns sample slots as cart-JSON-friendly list, or empty list
    if samples module isn't available."""
    try:
        from . import samples
        return samples.serialize_for_cart()
    except Exception:
        return []

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

    # Restore extra map layers (1..3). Backward-compat: old carts
    # without "map_layers" simply leave layers 1-3 empty.
    if "map_layers" in cart:
        _restore_map_layers(cart["map_layers"])
    else:
        _clear_extra_layers()

    # SFX/Music load, if available (rueckwaertskompatibel with v1)
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
    if "samples" in cart:
        try:
            from . import samples
            samples.restore_from_cart(cart["samples"])
        except Exception as e:
            print(f"Sample restore failed: {e}")

    # Code-Felder load (rueckwaertskompatibel with v1/v2)
    if "code" in cart:
        state.cart_code = cart["code"]
    if "code_file" in cart:
        state.cart_code_file = cart["code_file"]
    if "meta" in cart:
        state.cart_meta = cart["meta"] or {}
    # If code editor was active: refresh lines buffer
    if hasattr(state, "ce_lines"):
        from . import code_editor
        state.ce_lines = code_editor._text_to_lines(state.cart_code)
        state.ce_cur_row = 0
        state.ce_cur_col = 0
        state.ce_dirty = False

    print(f"Cart loaded: {filename}")
    return True
