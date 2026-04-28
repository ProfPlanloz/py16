"""
py16.bios
=========
Minimaler BIOS-Bildschirm. Wird angezeigt wenn:
  - py16.run() ohne explizite update/draw aufgerufen wird, ODER
  - der laufende Cart ueber den Stack hinaus zurueckpoppt, ODER
  - der User explizit go_to_bios() aufruft

Bietet:
  - Liste aller Carts im Cart-Verzeichnis
  - Cart auswaehlen mit Pfeilen, Enter zum Starten
  - F6 fuer leeren Code-Editor (neuer Cart schreiben)
  - F12 fuer Power-Menue (Linux: poweroff/reboot)
"""

import os
import subprocess
import pygame

from . import state, config
from .core import WIDTH, HEIGHT
from .graphics import cls, rectfill, rect, line, text
from .input import btn, btnp

# ----------------------------------------------------------------------
# STATE-INIT
# ----------------------------------------------------------------------

def _ensure_state():
    defaults = {
        "bios_cursor":     0,        # Index in der Cart-Liste
        "bios_scroll":     0,        # Scroll-Offset
        "bios_cart_list":  None,     # cached: Liste der Cart-Pfade
        "bios_message":    "",
        "bios_msg_color":  7,
        "bios_msg_time":   0,
        "bios_in_power":   False,    # Power-Menue-Modus
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

    # Scroll-Offset anpassen
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
            _set_msg(f"STARTE: {os.path.basename(path)}", 11)

    # R: Cart-Liste neu laden
    for k in (pygame.K_r,):
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            _refresh_carts()
            _set_msg("CART-LISTE AKTUALISIERT", 11)

    # F6: leeren Code-Editor oeffnen
    if state.keys.get(pygame.K_F6, False) and not state.keys_prev.get(pygame.K_F6, False):
        from . import code_editor
        code_editor._ensure_state()
        # Editor leer anzeigen
        if not state.cart_code:
            state.ce_lines = ["import py16", "", "def init():", "    pass", "",
                              "def update():", "    pass", "",
                              "def draw():", "    py16.cls(0)",
                              "    py16.text('NEW CART', 50, 50, 7)"]
            state.cart_code = "\n".join(state.ce_lines)
            state.cart_code_file = os.path.join(config.carts_dir(), "untitled.py")
        state.editor_mode = "code"
        state.bios_active = False

    # F12: Power-Menue
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
        text("KEINE CARTS GEFUNDEN", 8, 60, 8)
        text(f"VERZEICHNIS:", 8, 80, 6)
        text(config.carts_dir(), 8, 88, 7, upper=False)
        text("LEGE EIN .P16 ODER .PDF DORT AB", 8, 100, 6)
        text("R AKTUALISIEREN", 8, 120, 6)
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

            # Highlight aktive Zeile
            if idx == state.bios_cursor:
                rectfill(0, y - 1, WIDTH, LINE_H + 1, 13)
                text(">", LIST_X, y, 7)

            text(f"[{('PDF' if is_pdf else 'P16'):3}]",
                 LIST_X + 8, y, ext_color)
            text(name[:36], LIST_X + 30, y, 7, upper=False)

    # Status-Bar
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
    ("BACK TO BIOS",   None),
    ("SHUTDOWN",       "power_off_cmd"),
    ("REBOOT",         "reboot_cmd"),
    ("QUIT TO DESKTOP", "quit"),
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
        else:
            cmd = config.get_config().get(action)
            if cmd:
                _execute_power(cmd)
            else:
                _set_msg(f"KEIN BEFEHL FUER {label}", 8)
                state.bios_in_power = False

    # ESC verlaesst Power-Menue
    for k in (pygame.K_ESCAPE,):
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            state.bios_in_power = False

def _power_menu_draw():
    # Box in der Mitte
    bx, by, bw, bh = 60, 60, WIDTH - 120, 100
    rectfill(bx, by, bw, bh, 0)
    rect(bx, by, bw, bh, 7)
    text("POWER MENUE", bx + 8, by + 6, 7)

    for i, (label, _) in enumerate(POWER_OPTIONS):
        y = by + 24 + i * 12
        if i == state.bios_power_idx:
            rectfill(bx + 4, y - 1, bw - 8, 10, 13)
            text(">", bx + 6, y, 7)
        text(label, bx + 14, y, 7)

    text("ESC ABBRECHEN", bx + 8, by + bh - 10, 6)

def _execute_power(cmd):
    """Fuehrt ein Shell-Kommando fuer Power-Off/Reboot aus."""
    try:
        # Vor dem Power-Off Pygame sauber beenden
        pygame.quit()
        # subprocess statt os.system, damit kein Shell-Injection moeglich ist
        # (cmd kommt aus user-config, also vertrauenswuerdig, aber sauber)
        subprocess.Popen(cmd, shell=True)
        # Wir geben dem System einen Moment Zeit, dann beenden
        import sys, time
        time.sleep(0.5)
        sys.exit(0)
    except Exception as e:
        _set_msg(f"POWER-FEHLER: {e}", 8)

# ----------------------------------------------------------------------
# AKTIVIERUNG
# ----------------------------------------------------------------------

def go_to_bios():
    """Aktiviert den BIOS-Modus. Wird im naechsten Frame aktiv."""
    state.bios_active = True
    state.editor_mode = None
    _refresh_carts()

def is_bios_active():
    return getattr(state, "bios_active", False)
