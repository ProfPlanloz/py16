"""
py16.cart_runtime
=================
Cart-Switch at runtime. Zwei Mechaniken:

  run_cart(path)   - Reset: old cart is discarded, new cart runs
  push_cart(path)  - Stack: old cart is remembered, new runs "on top"
  pop_cart()       - vom Stack back zum vorherigen Cart
  cart_stack_depth() - How many carts are on the stack?

Carts on the stack buffer their complete engine state (sprite sheet,
map, flags, SFX, music, code, code-editor state). This allows a
mini-game or menu to be its own cart that returns with pop_cart()
back zum callden Cart kommt.
"""

import os
import io

from . import state

# ----------------------------------------------------------------------
# STATE INIT
# ----------------------------------------------------------------------

def _ensure_state():
    if not hasattr(state, "cart_stack"):
        state.cart_stack = []          # list of snapshots
        state.next_cart_action = None  # ("run"|"push"|"pop", path)

# ----------------------------------------------------------------------
# SNAPSHOT
# ----------------------------------------------------------------------

def _snapshot_engine():
    """Snapshot of all relevant state fields.
    Placed on the stack so pop_cart() can restore."""
    import pygame

    # Copy sprite sheet as bytes buffer (else shared-mutable)
    sheet_copy = None
    if state.sprite_sheet is not None:
        sheet_copy = pygame.Surface(state.sprite_sheet.get_size())
        sheet_copy.blit(state.sprite_sheet, (0, 0))

    snap = {
        "sheet":          sheet_copy,
        "map_data":       [list(row) for row in state.map_data] if state.map_data else None,
        "sprite_flags":   list(state.sprite_flags) if state.sprite_flags else None,
        "sfx_patches":    [_clone_sfx(p) for p in getattr(state, "sfx_patches", [])],
        "music_patterns": [dict(p, channels=list(p["channels"])) for p in getattr(state, "music_patterns", [])],
        "music_tracks":   [list(t) for t in getattr(state, "music_tracks", [])],
        "cart_code":      getattr(state, "cart_code", ""),
        "cart_code_file": getattr(state, "cart_code_file", None),
        "cart_update_fn": getattr(state, "cart_update_fn", None),
        "cart_draw_fn":   getattr(state, "cart_draw_fn", None),
        "cart_init_fn":   getattr(state, "cart_init_fn", None),
        "cam":            (state.cam_x, state.cam_y),
    }
    return snap

def _clone_sfx(patch):
    return {
        "speed":      patch["speed"],
        "loop_start": patch["loop_start"],
        "loop_end":   patch["loop_end"],
        "notes":      [tuple(n) for n in patch["notes"]],
    }

def _restore_engine(snap):
    """Restores engine state from a snapshot."""
    import pygame
    if snap["sheet"] is not None and state.sprite_sheet is not None:
        state.sprite_sheet.blit(snap["sheet"], (0, 0))
    if snap["map_data"] is not None:
        state.map_data[:] = [list(row) for row in snap["map_data"]]
    if snap["sprite_flags"] is not None:
        state.sprite_flags[:] = list(snap["sprite_flags"])
    if hasattr(state, "sfx_patches"):
        for i, p in enumerate(snap["sfx_patches"]):
            if i < len(state.sfx_patches):
                state.sfx_patches[i] = _clone_sfx(p)
    if hasattr(state, "music_patterns"):
        for i, p in enumerate(snap["music_patterns"]):
            if i < len(state.music_patterns):
                state.music_patterns[i] = dict(p, channels=list(p["channels"]))
    if hasattr(state, "music_tracks"):
        for i, t in enumerate(snap["music_tracks"]):
            if i < len(state.music_tracks):
                state.music_tracks[i] = list(t)
    state.cart_code      = snap["cart_code"]
    state.cart_code_file = snap["cart_code_file"]
    state.cart_update_fn = snap["cart_update_fn"]
    state.cart_draw_fn   = snap["cart_draw_fn"]
    state.cart_init_fn   = snap["cart_init_fn"]
    state.cam_x, state.cam_y = snap["cam"]

    # Clear editor state caches (doesn't fit new code)
    if hasattr(state, "ce_lines"):
        from . import code_editor
        state.ce_lines = code_editor._text_to_lines(state.cart_code or "")
        state.ce_cur_row = 0
        state.ce_cur_col = 0
        state.ce_sel_anchor = None
        state.ce_dirty = False

# ----------------------------------------------------------------------
# DEFER MECHANISM
# ----------------------------------------------------------------------
# The calls run_cart(path) etc. only set a flag that is checked in
# main loop between Frames ausgewertet wird. Sonst kaem es zu
# would arise (cart calling itself in update).

def _request(action, path=None):
    _ensure_state()
    state.next_cart_action = (action, path)

def run_cart(path):
    """Discards den currentn Cart und startet path frisch.
    Reset semantics: stack is cleared, old engine state lost."""
    _request("run", path)

def push_cart(path):
    """Pushes current cart onto the stack and starts path on top.
    Mit pop_cart() kommt man back."""
    _request("push", path)

def pop_cart():
    """Beendet currentn Cart und kehrt zum darunterliegenden back.
    Does nothing if the stack is empty."""
    _request("pop", None)

def cart_stack_depth():
    _ensure_state()
    return len(state.cart_stack)

def current_cart_file():
    """Path of currently running cart (or None when in BIOS)."""
    return getattr(state, "cart_code_file", None)

# ----------------------------------------------------------------------
# EXECUTION (called by core.run() each frame)
# ----------------------------------------------------------------------

def process_pending_actions():
    """In der main loop between Frames called.
    Returns True if a cart switch happened."""
    _ensure_state()
    if state.next_cart_action is None:
        return False

    action, path = state.next_cart_action
    state.next_cart_action = None

    try:
        if action == "run":
            _do_run(path)
        elif action == "push":
            _do_push(path)
        elif action == "pop":
            _do_pop()
    except Exception as e:
        # Store the error visibly for the render loop instead of just printing.
        # Im fullscreen ist der Print sonst nicht zu sehen.
        import traceback
        tb = traceback.format_exc(limit=3)
        state.cart_load_error = {
            "action": action,
            "path":   path,
            "msg":    str(e),
            "trace":  tb,
        }
        print(f"Cart switch failed ({action} {path}): {e}")
        # Engine stays in old state but doesn't automatically go to BIOS
    return True

def _load_cart_file(path):
    """Loads einen Cart (.p16 oder .pdf), kompiliert seinen Code,
    sets update_fn/draw_fn/init_fn in state."""
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Cart not found: {path}")
    from .cart import load_cart
    ok = load_cart(path)
    if not ok:
        raise RuntimeError(f"Cart load failed: {path}")

    # Compile code and call init()
    from . import code_editor
    code_editor._ensure_state()
    code_editor.state.cart_code_file = path
    ok2, msg = code_editor.execute_code()
    if not ok2:
        raise RuntimeError(f"Cart code error: {msg}")

def _do_run(path):
    """Reset variant: clear stack, new cart from scratch."""
    state.cart_stack.clear()
    _load_cart_file(path)
    state.editor_mode = None
    state.bios_active = False

def _do_push(path):
    """Push-Variante: alten Stand sichern, neuen load."""
    snap = _snapshot_engine()
    _load_cart_file(path)
    state.cart_stack.append(snap)
    state.editor_mode = None
    state.bios_active = False

def _do_pop():
    """Pop-Variante: zum vorherigen Cart back."""
    if not state.cart_stack:
        # Nothing to pop - stay here
        return
    snap = state.cart_stack.pop()
    _restore_engine(snap)
    state.editor_mode = None
    state.bios_active = False
