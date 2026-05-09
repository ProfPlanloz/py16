"""
py16.bios
=========
Minimal BIOS screen. Shown when:
  - py16.run() is called without explicit update/draw, OR
  - the running cart pops off the stack, OR
  - the user explicitly calls go_to_bios()

Provides:
  - List of all carts in the cart directory
  - Select a cart with arrows, Enter to start
  - F6 to open empty code editor (write new cart)
  - F12 for power menu (Linux: poweroff/reboot)
"""

import os
import subprocess
import pygame

from . import state, config
from .core import WIDTH, HEIGHT
from .graphics import cls, rectfill, rect, line, text
from .input import btn, btnp

# ----------------------------------------------------------------------
# STATE INIT
# ----------------------------------------------------------------------

def _ensure_state():
    defaults = {
        "bios_cursor":     0,        # Index in cart list
        "bios_scroll":     0,        # Scroll offset
        "bios_cart_list":  None,     # cached: list of cart paths
        "bios_message":    "",
        "bios_msg_color":  7,
        "bios_msg_time":   0,
        "bios_in_power":   False,    # Power menu mode
        "bios_power_idx":  0,
    }
    for k, v in defaults.items():
        if not hasattr(state, k):
            setattr(state, k, v)

def _refresh_carts():
    state.bios_cart_list = config.list_carts()

def _set_msg(msg, color=7):
    state.bios_message = msg
    state.bios_msg_color = color
    state.bios_msg_time = state.frame_count

# ----------------------------------------------------------------------
# UPDATE
# ----------------------------------------------------------------------

VISIBLE_LINES = 18
LINE_H = 8
LIST_X = 8
LIST_Y = 30

def bios_update():
    _ensure_state()
    if state.bios_cart_list is None:
        _refresh_carts()

    if state.bios_in_power:
        _power_menu_update()
        return

    if btnp('up'):
        state.bios_cursor = max(0, state.bios_cursor - 1)
    if btnp('down'):
        state.bios_cursor = min(len(state.bios_cart_list) - 1,
                                state.bios_cursor + 1)
        if state.bios_cursor < 0:
            state.bios_cursor = 0

    # PageUp/Down
    for k, dx in [(pygame.K_PAGEUP, -VISIBLE_LINES),
                  (pygame.K_PAGEDOWN, VISIBLE_LINES)]:
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            state.bios_cursor = max(0, min(len(state.bios_cart_list) - 1,
                                           state.bios_cursor + dx))

    # Scroll offset adjust
    if state.bios_cursor < state.bios_scroll:
        state.bios_scroll = state.bios_cursor
    if state.bios_cursor >= state.bios_scroll + VISIBLE_LINES:
        state.bios_scroll = state.bios_cursor - VISIBLE_LINES + 1

    # Enter / Space: Cart starten
    if btnp('enter') or btnp('space'):
        if state.bios_cart_list and 0 <= state.bios_cursor < len(state.bios_cart_list):
            path = state.bios_cart_list[state.bios_cursor]
            from . import cart_runtime
            cart_runtime.run_cart(path)
            _set_msg(f"STARTING: {os.path.basename(path)}", 11)

    # R: Cart-Liste neu load
    for k in (pygame.K_r,):
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            _refresh_carts()
            _set_msg("CART LIST REFRESHED", 11)

    # F6: open empty code editor
    if state.keys.get(pygame.K_F6, False) and not state.keys_prev.get(pygame.K_F6, False):
        from . import code_editor
        code_editor._ensure_state()
        # Show editor empty
        if not state.cart_code:
            state.ce_lines = ["import py16", "", "def init():", "    pass", "",
                              "def update():", "    pass", "",
                              "def draw():", "    py16.cls(0)",
                              "    py16.text('NEW CART', 50, 50, 7)"]
            state.cart_code = "\n".join(state.ce_lines)
            state.cart_code_file = os.path.join(config.carts_dir(), "untitled.py")
        state.editor_mode = "code"
        state.bios_active = False

    # F12: Power menu
    if state.keys.get(pygame.K_F12, False) and not state.keys_prev.get(pygame.K_F12, False):
        state.bios_in_power = True
        state.bios_power_idx = 0

# ----------------------------------------------------------------------
# DRAW
# ----------------------------------------------------------------------

def bios_draw():
    _ensure_state()
    if state.bios_cart_list is None:
        _refresh_carts()

    cls(1)   # dunkles Blau

    # Top-Bar
    rectfill(0, 0, WIDTH, 16, 13)
    text("PY-16 BIOS", 4, 2, 7)
    text(f"CARTS:{len(state.bios_cart_list):03d}", WIDTH - 64, 2, 7)
    text(config.carts_dir()[:32], 4, 9, 5)

    if state.bios_in_power:
        _power_menu_draw()
        return

    # Cart-Liste
    if not state.bios_cart_list:
        text("NO CARTS FOUND", 8, 60, 8)
        text(f"DIRECTORY:", 8, 80, 6)
        text(config.carts_dir(), 8, 88, 7, upper=False)
        text("PUT A .P16 OR .PDF THERE", 8, 100, 6)
        text("R RELOAD", 8, 120, 6)
    else:
        for i in range(VISIBLE_LINES):
            idx = state.bios_scroll + i
            if idx >= len(state.bios_cart_list):
                break
            y = LIST_Y + i * LINE_H
            path = state.bios_cart_list[idx]
            name = os.path.basename(path)
            is_pdf = name.lower().endswith(".pdf")
            ext_color = 11 if is_pdf else 12   # PDF gruen, .p16 blau

            # Highlight active row
            if idx == state.bios_cursor:
                rectfill(0, y - 1, WIDTH, LINE_H + 1, 13)
                text(">", LIST_X, y, 7)

            text(f"[{('PDF' if is_pdf else 'P16'):3}]",
                 LIST_X + 8, y, ext_color)
            text(name[:36], LIST_X + 30, y, 7, upper=False)

    # Status bar
    sy = HEIGHT - 18
    rectfill(0, sy, WIDTH, 18, 13)
    if state.bios_message and (state.frame_count - state.bios_msg_time) < 180:
        text(state.bios_message, 4, sy + 1, state.bios_msg_color)
    else:
        text("UP/DOWN NAV  ENTER START  R RELOAD",
             4, sy + 1, 6)
    text("F6 NEW CART  F12 POWER  ESC QUIT", 4, sy + 9, 6)

# ----------------------------------------------------------------------
# POWER-MENUE
# ----------------------------------------------------------------------

POWER_OPTIONS = [
    ("BACK TO BIOS",     None),
    ("CLEAN COVER CACHE", "clean_cache"),
    ("SHUTDOWN",         "power_off_cmd"),
    ("REBOOT",           "reboot_cmd"),
    ("QUIT TO DESKTOP",  "quit"),
]

def _power_menu_update():
    if btnp('up'):
        state.bios_power_idx = max(0, state.bios_power_idx - 1)
    if btnp('down'):
        state.bios_power_idx = min(len(POWER_OPTIONS) - 1,
                                   state.bios_power_idx + 1)
    if btnp('enter') or btnp('space'):
        label, action = POWER_OPTIONS[state.bios_power_idx]
        if action is None:
            state.bios_in_power = False
        elif action == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif action == "clean_cache":
            _do_clean_cache()
            state.bios_in_power = False
        else:
            cmd = config.get_config().get(action)
            if cmd:
                _execute_power(cmd)
            else:
                _set_msg(f"NO COMMAND FOR {label}", 8)
                state.bios_in_power = False

    # ESC exits power menu
    for k in (pygame.K_ESCAPE,):
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            state.bios_in_power = False

def _do_clean_cache():
    """Run cover cache cleanup and show feedback in BIOS status bar."""
    try:
        from . import cart_covers
        result = cart_covers.cleanup_cache(remove_orphans=True)
        kb = result["freed_bytes"] // 1024
        if result["removed"] == 0:
            _set_msg("CACHE CLEAN: NOTHING TO REMOVE", 11)
        else:
            _set_msg(f"REMOVED {result['removed']} FILES ({kb}KB)", 11)
    except Exception as e:
        _set_msg(f"CACHE CLEAN FAILED: {e}", 8)

def _power_menu_draw():
    # Box in der Mitte
    bx, by, bw, bh = 60, 60, WIDTH - 120, 100
    rectfill(bx, by, bw, bh, 0)
    rect(bx, by, bw, bh, 7)
    text("POWER MENU", bx + 8, by + 6, 7)

    for i, (label, _) in enumerate(POWER_OPTIONS):
        y = by + 24 + i * 12
        if i == state.bios_power_idx:
            rectfill(bx + 4, y - 1, bw - 8, 10, 13)
            text(">", bx + 6, y, 7)
        text(label, bx + 14, y, 7)

    text("ESC CANCEL", bx + 8, by + bh - 10, 6)

def _execute_power(cmd):
    """Executes a shell command for power-off/reboot."""
    try:
        # Cleanly shut down pygame before power-off
        pygame.quit()
        # subprocess instead of os.system to avoid shell injection
        # (cmd comes from user config, so trusted, but clean)
        subprocess.Popen(cmd, shell=True)
        # Give the system a moment, then exit
        import sys, time
        time.sleep(0.5)
        sys.exit(0)
    except Exception as e:
        _set_msg(f"POWER ERROR: {e}", 8)

# ----------------------------------------------------------------------
# ACTIVATION
# ----------------------------------------------------------------------

def go_to_bios():
    """Activates BIOS mode. Becomes active next frame."""
    state.bios_active = True
    state.editor_mode = None
    _refresh_carts()

def is_bios_active():
    return getattr(state, "bios_active", False)
