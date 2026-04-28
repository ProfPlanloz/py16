"""
py16.input
==========
Tastatur- und Maus-Eingabe. btn() = gedrueckt halten,
btnp() = nur in dem Frame, in dem die Taste neu gedrueckt wurde.
"""

import pygame

from . import state

# ======================================================================
# TASTATUR
# ======================================================================

KEYMAP = {
    'up':    pygame.K_UP,    'down':  pygame.K_DOWN,
    'left':  pygame.K_LEFT,  'right': pygame.K_RIGHT,
    'z':     pygame.K_z,     'x':     pygame.K_x,
    'a':     pygame.K_a,     's':     pygame.K_s,
    'space': pygame.K_SPACE, 'enter': pygame.K_RETURN,
    'shift': pygame.K_LSHIFT,
}

def btn(key_name):
    return state.keys.get(KEYMAP.get(key_name, -1), False)

def btnp(key_name):
    k = KEYMAP.get(key_name, -1)
    return state.keys.get(k, False) and not state.keys_prev.get(k, False)

# ======================================================================
# MAUS
# ======================================================================

def mouse_x():
    return state.mouse_x

def mouse_y():
    return state.mouse_y

def mouse_btn(idx=0):
    """0 = links, 1 = mitte, 2 = rechts."""
    return 0 <= idx < 3 and state.mouse_btn[idx]

def mouse_btnp(idx=0):
    return (0 <= idx < 3
            and state.mouse_btn[idx]
            and not state.mouse_btn_prev[idx])
