"""
py16.editor_samples
====================
Sample editor (F10). Loads .ogg/.wav samples into the 16 sample slots,
sets base notes, names, and lets you preview at different pitches.

Layout:
    +-------------+----------------------+
    | SLOT LIST   |  DETAILS / LOAD      |
    | 16 entries  |                      |
    +-------------+----------------------+

Controls:
    Up/Down       Select slot
    Tab           Cycle focus: list / name field / path field
    Letters       Edit text in active field
    Backspace     Delete character
    Space         Play active slot at base note
    Z/X/C/V...    Piano-style note preview
    , / .         Adjust base note -1/+1 semitone
    Ctrl+L        Load sample from path field
    Ctrl+D / Del  Clear active slot
    Esc / F10     Exit editor
"""

import os
import pygame

from . import state, samples, sfx_data
from .core import WIDTH, HEIGHT
from .graphics import cls, rectfill, rect, line, text
from .input import btn, btnp

# Reuse piano constants from the audio editor
from .editors_audio import PIANO_KEYS_LOW, PIANO_KEYS_HIGH, PIANO_BASE_OCTAVE

# ----------------------------------------------------------------------
# STATE
# ----------------------------------------------------------------------

FOCUS_LIST = 0
FOCUS_NAME = 1
FOCUS_PATH = 2
N_FOCUS = 3

def _ensure_state():
    defaults = {
        "samp_slot":   0,
        "samp_focus":  FOCUS_LIST,
        "samp_path":   "",
        "samp_status": "",
        "samp_status_color": 7,
        "samp_status_time":  0,
    }
    for k, v in defaults.items():
        if not hasattr(state, k):
            setattr(state, k, v)
    samples.init_state()

def _set_status(msg, color=7):
    state.samp_status = msg
    state.samp_status_color = color
    state.samp_status_time = state.frame_count

def _just_pressed(key):
    return state.keys.get(key, False) and not state.keys_prev.get(key, False)

# ----------------------------------------------------------------------
# UPDATE
# ----------------------------------------------------------------------

def sample_editor_update():
    _ensure_state()
    ctrl  = state.keys.get(pygame.K_LCTRL, False) or state.keys.get(pygame.K_RCTRL, False)
    shift = state.keys.get(pygame.K_LSHIFT, False) or state.keys.get(pygame.K_RSHIFT, False)

    # Ctrl+L: load sample from path field
    if ctrl and _just_pressed(pygame.K_l):
        _do_load()
        return

    # Ctrl+D: clear active slot
    if ctrl and _just_pressed(pygame.K_d):
        _do_clear()
        return
    if _just_pressed(pygame.K_DELETE):
        _do_clear()
        return

    # Tab: cycle focus
    if _just_pressed(pygame.K_TAB):
        if shift:
            state.samp_focus = (state.samp_focus - 1) % N_FOCUS
        else:
            state.samp_focus = (state.samp_focus + 1) % N_FOCUS
        return

    # Routing by focus
    if state.samp_focus == FOCUS_LIST:
        _list_input()
    elif state.samp_focus == FOCUS_NAME:
        _name_input(shift)
    elif state.samp_focus == FOCUS_PATH:
        _path_input(shift)

    # Piano-style preview always active (regardless of focus, except path field
    # since that needs letters as text input)
    if state.samp_focus != FOCUS_PATH and state.samp_focus != FOCUS_NAME:
        _piano_preview()

    # , / . : adjust base note
    if _just_pressed(pygame.K_COMMA) and not shift:
        slot = state.samples[state.samp_slot]
        if slot["data"]:
            slot["base_note"] = max(0, slot["base_note"] - 1)
            samples._purge_play_cache(state.samp_slot)
    if _just_pressed(pygame.K_PERIOD) and not shift:
        slot = state.samples[state.samp_slot]
        if slot["data"]:
            slot["base_note"] = min(95, slot["base_note"] + 1)
            samples._purge_play_cache(state.samp_slot)

def _list_input():
    if btnp('up'):
        state.samp_slot = max(0, state.samp_slot - 1)
    if btnp('down'):
        state.samp_slot = min(samples.NUM_SAMPLES - 1, state.samp_slot + 1)
    # Space plays the slot at base note
    if _just_pressed(pygame.K_SPACE):
        slot = state.samples[state.samp_slot]
        if slot["data"]:
            samples.play_sample(state.samp_slot, channel=7)
            _set_status(f"PLAYED SLOT {state.samp_slot:02d}", 11)
        else:
            _set_status("SLOT IS EMPTY", 8)

def _name_input(shift):
    slot = state.samples[state.samp_slot]
    if _just_pressed(pygame.K_BACKSPACE):
        slot["name"] = slot["name"][:-1]
        return
    for k in list(state.keys.keys()):
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            ch = _key_to_char(k, shift)
            if ch and len(slot["name"]) < 16:
                slot["name"] += ch.upper()
                return

def _path_input(shift):
    if _just_pressed(pygame.K_BACKSPACE):
        state.samp_path = state.samp_path[:-1]
        return
    for k in list(state.keys.keys()):
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            ch = _key_to_char(k, shift)
            if ch and len(state.samp_path) < 200:
                state.samp_path += ch
                return

def _key_to_char(key, shift):
    if pygame.K_a <= key <= pygame.K_z:
        ch = chr(key)
        return ch.upper() if shift else ch
    if pygame.K_0 <= key <= pygame.K_9:
        if shift:
            return ")!@#$%^&*("[key - pygame.K_0]
        return chr(key)
    special = {
        pygame.K_SPACE:  ' ',
        pygame.K_MINUS:  '_' if shift else '-',
        pygame.K_PERIOD: '.',
        pygame.K_SLASH:  '/',
    }
    return special.get(key)

def _piano_preview():
    """Plays active slot at piano-key pitch."""
    slot = state.samples[state.samp_slot]
    if not slot["data"]:
        return
    base = PIANO_BASE_OCTAVE * 12
    for k, semi in {**PIANO_KEYS_LOW, **PIANO_KEYS_HIGH}.items():
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            note = base + semi
            samples.play_sample(state.samp_slot, note=note, channel=7)
            return

# ----------------------------------------------------------------------
# ACTIONS
# ----------------------------------------------------------------------

def _do_load():
    path = state.samp_path.strip()
    if not path:
        _set_status("NO PATH GIVEN", 8)
        return
    try:
        samples.load_sample(state.samp_slot, path)
        slot = state.samples[state.samp_slot]
        kb = (len(slot["data"]) * 3 // 4) // 1024 if slot["data"] else 0
        _set_status(f"LOADED {kb}KB INTO SLOT {state.samp_slot:02d}", 11)
    except FileNotFoundError:
        _set_status(f"NOT FOUND: {os.path.basename(path)}", 8)
    except ValueError as e:
        _set_status(str(e).upper()[:40], 8)
    except Exception as e:
        _set_status(f"LOAD ERROR: {e}", 8)

def _do_clear():
    if not state.samples[state.samp_slot]["data"]:
        _set_status("SLOT ALREADY EMPTY", 6)
        return
    samples.clear_sample(state.samp_slot)
    _set_status(f"CLEARED SLOT {state.samp_slot:02d}", 11)

# ----------------------------------------------------------------------
# DRAW
# ----------------------------------------------------------------------

def sample_editor_draw():
    _ensure_state()
    cls(0)

    # Title bar
    rectfill(0, 0, WIDTH, 12, 13)
    text("SAMPLE EDIT", 4, 3, 7)
    text(f"SLOT {state.samp_slot:02d}/{samples.NUM_SAMPLES - 1:02d}",
         WIDTH - 56, 3, 11)

    # Layout: left = slot list, right = details + load
    _draw_slot_list(4, 16, 124, 156)
    _draw_details(132, 16, WIDTH - 136, 80)
    _draw_load_panel(132, 100, WIDTH - 136, 72)

    # Status / help
    _draw_status_bar()

# ---------- Slot list ----------

def _draw_slot_list(x, y, w, h):
    active_focus = (state.samp_focus == FOCUS_LIST)
    border_col = 8 if active_focus else 5
    rect(x - 1, y - 1, w + 2, h + 2, border_col)
    text("SLOTS", x + 2, y, 11)

    row_h = 9
    list_y = y + 8
    list_h = h - 8
    n_visible = list_h // row_h
    # Scroll so selected is visible
    scroll = max(0, state.samp_slot - n_visible + 2)
    scroll = min(scroll, max(0, samples.NUM_SAMPLES - n_visible))

    for vis in range(n_visible):
        i = scroll + vis
        if i >= samples.NUM_SAMPLES:
            break
        ry = list_y + vis * row_h
        slot = state.samples[i]

        # Highlight if selected
        if i == state.samp_slot:
            rectfill(x + 1, ry, w - 2, row_h - 1, 1)
            text(">", x + 2, ry + 2, 7)

        # Slot index in left
        col = 7 if i == state.samp_slot else 6
        text(f"{i:02d}", x + 8, ry + 2, col)

        if slot["data"]:
            name = slot["name"][:10] if slot["name"] else "(unnamed)"
            kb = (len(slot["data"]) * 3 // 4) // 1024
            text(name, x + 22, ry + 2, col)
            # Tiny size badge
            text(f"{kb:3d}K", x + w - 22, ry + 2, 6)
        else:
            text("(empty)", x + 22, ry + 2, 5)

# ---------- Details panel ----------

def _draw_details(x, y, w, h):
    active_focus = (state.samp_focus == FOCUS_NAME)
    rect(x - 1, y - 1, w + 2, h + 2, 5)
    text("DETAILS", x + 2, y, 11)

    slot = state.samples[state.samp_slot]
    if not slot["data"]:
        text("EMPTY SLOT", x + 4, y + 16, 6)
        text("LOAD A SAMPLE BELOW", x + 4, y + 26, 6)
        return

    # Format / size / length
    fmt  = (slot["format"] or "?").upper()
    kb   = (len(slot["data"]) * 3 // 4) // 1024
    if slot["_pcm"] and slot["_sr"]:
        sec = len(slot["_pcm"]) / slot["_sr"]
        len_str = f"{sec:.2f}s"
    else:
        len_str = "-"
    text(f"FMT: {fmt}", x + 4, y + 14, 6)
    text(f"SIZE: {kb}KB", x + 4 + 50, y + 14, 6)
    text(f"LEN: {len_str}", x + 4, y + 24, 6)

    # Base note: editable via , / .
    note = slot["base_note"]
    note_name = sfx_data.note_name(note)
    text("BASE:", x + 4, y + 38, 6)
    text(f"{note_name} ({note})", x + 36, y + 38, 11)
    text(",/. ADJUST", x + 4, y + 46, 6)

    # Name field
    name_active = active_focus
    name_label_col = 7 if name_active else 6
    text("NAME:", x + 4, y + 58, name_label_col)
    box_y = y + 65
    box_w = w - 8
    rect(x + 4, box_y, box_w, 11, 8 if name_active else 5)
    rectfill(x + 5, box_y + 1, box_w - 2, 9, 1)
    display = slot["name"]
    if name_active and (state.frame_count // 30) % 2 == 0:
        display += "_"
    text(display, x + 7, box_y + 3, 7)

# ---------- Load panel ----------

def _draw_load_panel(x, y, w, h):
    active_focus = (state.samp_focus == FOCUS_PATH)
    rect(x - 1, y - 1, w + 2, h + 2, 5)
    text("LOAD", x + 2, y, 11)

    # Path field
    path_label_col = 7 if active_focus else 6
    text("PATH:", x + 4, y + 12, path_label_col)
    box_y = y + 19
    box_w = w - 8
    rect(x + 4, box_y, box_w, 11, 8 if active_focus else 5)
    rectfill(x + 5, box_y + 1, box_w - 2, 9, 1)
    display = state.samp_path
    if active_focus and (state.frame_count // 30) % 2 == 0:
        display += "_"
    # Show the right end if too long
    max_visible = (box_w - 4) // 4
    if len(display) > max_visible:
        display = display[-max_visible:]
    text(display, x + 7, box_y + 3, 7, upper=False)

    # Hint
    text("OGG / WAV  MAX 256KB", x + 4, y + 34, 6)
    text("CTRL-L LOAD INTO SLOT", x + 4, y + 44, 11)
    text("CTRL-D / DEL CLEAR SLOT", x + 4, y + 54, 6)

# ---------- Status bar ----------

def _draw_status_bar():
    sy = HEIGHT - 16
    rectfill(0, sy, WIDTH, 16, 13)

    # Show recent status if any (3 sec)
    if state.samp_status and (state.frame_count - state.samp_status_time) < 180:
        text(state.samp_status, 4, sy + 1, state.samp_status_color)
    else:
        text("UP/DN SLOT  TAB FOCUS  SPACE PLAY", 4, sy + 1, 6)
    text("Z/X/C... PIANO  CTRL-L LOAD  ESC EXIT", 4, sy + 9, 6)

# ----------------------------------------------------------------------
# ACTIVATION
# ----------------------------------------------------------------------

def toggle():
    _ensure_state()
    if state.editor_mode == "samples":
        state.editor_mode = None
    else:
        state.editor_mode = "samples"
