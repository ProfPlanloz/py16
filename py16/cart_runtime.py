"""
py16.cart_runtime
=================
Cart-Wechsel zur Laufzeit. Zwei Mechaniken:

  run_cart(path)   - Reset: alter Cart wird verworfen, neuer Cart laeuft
  push_cart(path)  - Stack: alter Cart wird gemerkt, neuer laeuft "obendrauf"
  pop_cart()       - vom Stack zurueck zum vorherigen Cart
  cart_stack_depth() - Wieviele Carts sind gestackt?

Carts auf dem Stack puffern ihren kompletten Engine-State (Sprite-Sheet,
Map, Flags, SFX, Music, Code, Code-Editor-State). Das erlaubt es, ein
Mini-Spiel oder Menue als eigenen Cart zu haben, der mit pop_cart()
zurueck zum aufrufenden Cart kommt.
"""

import os
import io

from . import state

# ----------------------------------------------------------------------
# STATE-INIT
# ----------------------------------------------------------------------

def _ensure_state():
    if not hasattr(state, "cart_stack"):
        state.cart_stack = []          # Liste von Snapshots
        state.next_cart_action = None  # ("run"|"push"|"pop", path)

# ----------------------------------------------------------------------
# SNAPSHOT
# ----------------------------------------------------------------------

def _snapshot_engine():
    """Schnappschuss aller relevanten State-Felder.
    Wird auf den Stack gelegt, damit pop_cart() wiederherstellen kann."""
    import pygame

    # Sprite-Sheet als bytes-buffer kopieren (sonst shared-mutable)
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
    """Setzt den Engine-State aus einem Snapshot wieder her."""
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

    # Editor-State-Caches loeschen (passt nicht zum neuen Code)
    if hasattr(state, "ce_lines"):
        from . import code_editor
        state.ce_lines = code_editor._text_to_lines(state.cart_code or "")
        state.ce_cur_row = 0
        state.ce_cur_col = 0
        state.ce_sel_anchor = None
        state.ce_dirty = False

# ----------------------------------------------------------------------
# DEFER-MECHANIK
# ----------------------------------------------------------------------
# Die Aufrufe run_cart(path) etc. setzen NUR ein Flag, das in der
# Hauptschleife zwischen Frames ausgewertet wird. Sonst kaem es zu
# Re-Entrancy-Problemen (Cart ruft im Update sich selbst auf).

def _request(action, path=None):
    _ensure_state()
    state.next_cart_action = (action, path)

def run_cart(path):
    """Verwirft den aktuellen Cart und startet path frisch.
    Reset-Semantik: Stack wird geleert, alter Engine-Zustand verloren."""
    _request("run", path)

def push_cart(path):
    """Pusht aktuellen Cart auf den Stack und startet path obendrauf.
    Mit pop_cart() kommt man zurueck."""
    _request("push", path)

def pop_cart():
    """Beendet aktuellen Cart und kehrt zum darunterliegenden zurueck.
    Tut nichts, wenn der Stack leer ist."""
    _request("pop", None)

def cart_stack_depth():
    _ensure_state()
    return len(state.cart_stack)

def current_cart_file():
    """Pfad des aktuell laufenden Carts (oder None bei BIOS)."""
    return getattr(state, "cart_code_file", None)

# ----------------------------------------------------------------------
# AUSFUEHRUNG (von core.run() pro Frame aufgerufen)
# ----------------------------------------------------------------------

def process_pending_actions():
    """In der Hauptschleife zwischen Frames aufgerufen.
    Liefert True wenn ein Cart-Wechsel stattfand."""
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
        # Fehler sichtbar fuer den Render-Loop ablegen, statt nur Print.
        # Im Vollbild ist der Print sonst nicht zu sehen.
        import traceback
        tb = traceback.format_exc(limit=3)
        state.cart_load_error = {
            "action": action,
            "path":   path,
            "msg":    str(e),
            "trace":  tb,
        }
        print(f"Cart-Wechsel fehlgeschlagen ({action} {path}): {e}")
        # Engine bleibt in altem Zustand, geht aber nicht ins BIOS automatisch
    return True

def _load_cart_file(path):
    """Laedt einen Cart (.p16 oder .pdf), kompiliert seinen Code,
    setzt update_fn/draw_fn/init_fn in state."""
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Cart nicht gefunden: {path}")
    from .cart import load_cart
    ok = load_cart(path)
    if not ok:
        raise RuntimeError(f"Cart-Load fehlgeschlagen: {path}")

    # Code kompilieren und init() aufrufen
    from . import code_editor
    code_editor._ensure_state()
    code_editor.state.cart_code_file = path
    ok2, msg = code_editor.execute_code()
    if not ok2:
        raise RuntimeError(f"Cart-Code-Fehler: {msg}")

def _do_run(path):
    """Reset-Variante: Stack leeren, neuer Cart komplett neu."""
    state.cart_stack.clear()
    _load_cart_file(path)
    state.editor_mode = None
    state.bios_active = False

def _do_push(path):
    """Push-Variante: alten Stand sichern, neuen laden."""
    snap = _snapshot_engine()
    _load_cart_file(path)
    state.cart_stack.append(snap)
    state.editor_mode = None
    state.bios_active = False

def _do_pop():
    """Pop-Variante: zum vorherigen Cart zurueck."""
    if not state.cart_stack:
        # Nichts zu poppen - bleib wo du bist
        return
    snap = state.cart_stack.pop()
    _restore_engine(snap)
    state.editor_mode = None
    state.bios_active = False
