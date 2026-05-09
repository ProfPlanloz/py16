"""
py16.input
==========
Keyboard, mouse and gamepad input.

btn(name)            : held down right now (any source)
btnp(name)           : just pressed this frame (any source)
btn(name, player=N)  : held by specific player 1..4
btnp(name, player=N) : just pressed by specific player

Player 0 (default): any input source (keyboard + all gamepads).
Player 1: first controller, OR keyboard if no controllers are connected.
Player 2..4: second/third/fourth controller (no keyboard).
"""

import pygame

from . import state

# ======================================================================
# KEYBOARD MAPPING
# ======================================================================

KEYMAP = {
    'up':    pygame.K_UP,    'down':  pygame.K_DOWN,
    'left':  pygame.K_LEFT,  'right': pygame.K_RIGHT,
    'z':     pygame.K_z,     'x':     pygame.K_x,
    'a':     pygame.K_a,     's':     pygame.K_s,
    'w':     pygame.K_w,     'd':     pygame.K_d,
    'q':     pygame.K_q,     'e':     pygame.K_e,
    'space': pygame.K_SPACE, 'enter': pygame.K_RETURN,
    'shift': pygame.K_LSHIFT,
}

def _keyboard_is_held(key_name):
    return state.keys.get(KEYMAP.get(key_name, -1), False)

def _keyboard_just_pressed(key_name):
    k = KEYMAP.get(key_name, -1)
    return state.keys.get(k, False) and not state.keys_prev.get(k, False)

def _keyboard_eligible(player):
    """Does the keyboard count for this player slot?
    - player=0 (any source): always
    - player=1: only if no gamepads are connected (so single-player cart
                works without a gamepad attached)
    - player=2..4: never (those slots are gamepad-only)
    """
    if player == 0:
        return True
    if player == 1:
        from . import controller
        return controller.num_connected() == 0
    return False

def btn(key_name, player=0):
    """True if the given button is held this frame.

    player : 0 = any source (default, back-compat),
             1..4 = specific player slot.
    """
    from . import controller
    if _keyboard_eligible(player) and _keyboard_is_held(key_name):
        return True
    return controller.is_held(key_name, player=player)

def btnp(key_name, player=0):
    """True if the given button was just pressed this frame.

    player : 0 = any source (default, back-compat),
             1..4 = specific player slot.
    """
    from . import controller
    if _keyboard_eligible(player) and _keyboard_just_pressed(key_name):
        return True
    return controller.was_just_pressed(key_name, player=player)

# ======================================================================
# MOUSE
# ======================================================================

def mouse_x():
    return state.mouse_x

def mouse_y():
    return state.mouse_y

def mouse_btn(idx=0):
    """0 = left, 1 = middle, 2 = right."""
    return 0 <= idx < 3 and state.mouse_btn[idx]

def mouse_btnp(idx=0):
    return (0 <= idx < 3
            and state.mouse_btn[idx]
            and not state.mouse_btn_prev[idx])
