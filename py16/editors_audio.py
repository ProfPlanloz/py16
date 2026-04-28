"""
py16.editors_audio
==================
SFX-Editor (F3) und Music-Editor (F4).

SFX-EDITOR LAYOUT (256x224):
  Top-Bar:           ID, Speed, Loop-Punkte
  Notenraster:       32 Spalten x 4 Reihen (Note, Inst, Vol, FX)
                     Maus-Klick selektiert Zelle, +/- aendert Wert
  Tonleiter unten:   Klavier-Tasten Q-W-E-... = Live-Tonhoehe testen
  Hilfetexte

MUSIC-EDITOR LAYOUT:
  Top-Bar:           Track-ID, Pattern-Liste
  Pattern-Editor:    4 Kanaele x 16 Patterns -> SFX-IDs
  Track-Liste:       Sequenz von Pattern-IDs
"""

import pygame

from . import state, sfx_data, tracker
from .core import WIDTH, HEIGHT
from .graphics import cls, rectfill, rect, line, text
from .input import btn, btnp, mouse_btn, mouse_btnp

# ----------------------------------------------------------------------
# HELFER
# ----------------------------------------------------------------------

def _in_rect(mx, my, x, y, w, h):
    return x <= mx < x + w and y <= my < y + h

def _ensure_audio_state():
    """Sicherstellen, dass die Tracker-Daten existieren."""
    if not hasattr(state, "sfx_patches"):
        tracker.init_tracker_state()
    # Editor-spezifische State-Variablen
    if not hasattr(state, "se_cell_x"):
        state.se_cell_x = 0       # Spalte 0..31 im SFX-Editor
        state.se_cell_y = 0       # Reihe 0..3 (note/inst/vol/fx)
        state.se_sfx_id = 0       # aktiver SFX
    if not hasattr(state, "me_track_id"):
        state.me_track_id = 0
        state.me_cursor = 0       # Position in Track-Sequenz
        state.me_focus = "track"  # "track" | "pattern"
        state.me_pattern_id = 0
        state.me_pat_chan = 0     # 0..3

# ----------------------------------------------------------------------
# SFX-EDITOR
# ----------------------------------------------------------------------

# Layout
SE_GRID_X = 4
SE_GRID_Y = 22
SE_CELL_W = 7    # Spaltenbreite
SE_CELL_H = 8    # Zeilenhoehe
SE_ROWS = 4      # note, inst, vol, fx

# Klavier-Tastatur fuer Live-Test (untere Reihe = Stamm-Oktave)
# Mappt Tastencode -> Halbtonschritt-Offset von der Basis-Oktave
PIANO_KEYS_LOW = {
    pygame.K_z: 0,  pygame.K_s: 1,  pygame.K_x: 2,  pygame.K_d: 3,
    pygame.K_c: 4,  pygame.K_v: 5,  pygame.K_g: 6,  pygame.K_b: 7,
    pygame.K_h: 8,  pygame.K_n: 9,  pygame.K_j: 10, pygame.K_m: 11,
}
PIANO_KEYS_HIGH = {
    pygame.K_q: 12, pygame.K_2: 13, pygame.K_w: 14, pygame.K_3: 15,
    pygame.K_e: 16, pygame.K_r: 17, pygame.K_5: 18, pygame.K_t: 19,
    pygame.K_6: 20, pygame.K_y: 21, pygame.K_7: 22, pygame.K_u: 23,
}
PIANO_BASE_OCTAVE = 3   # Octave 3 (C3 = note 36)

def _piano_input():
    """Wenn Klavier-Taste gedrueckt: spielt Live-Note mit aktuellem Instrument."""
    sfx = state.sfx_patches[state.se_sfx_id]
    cell = sfx["notes"][state.se_cell_x]
    inst = cell[1]
    base = PIANO_BASE_OCTAVE * 12
    for k, semi in {**PIANO_KEYS_LOW, **PIANO_KEYS_HIGH}.items():
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            note = base + semi
            freq = sfx_data.note_freq(note)
            tracker._play_note_on_channel(7, freq, inst, 7, 200)
            # Auch in die aktuelle Notenzelle schreiben (komfortabel)
            sfx["notes"][state.se_cell_x] = (note, inst, max(cell[2], 5), cell[3])

def _change_cell_value(delta):
    """Aktuelle Zelle veraendern - je nach Reihe."""
    sfx = state.sfx_patches[state.se_sfx_id]
    cell = list(sfx["notes"][state.se_cell_x])
    row = state.se_cell_y
    if row == 0:    # Note
        if cell[0] == sfx_data.NOTE_EMPTY:
            cell[0] = 36   # C3 als Default
        else:
            cell[0] = max(0, min(63, cell[0] + delta))
    elif row == 1:  # Instrument
        cell[1] = (cell[1] + delta) % 8
    elif row == 2:  # Volume
        cell[2] = max(0, min(7, cell[2] + delta))
    elif row == 3:  # FX
        cell[3] = (cell[3] + delta) % 8
    sfx["notes"][state.se_cell_x] = tuple(cell)

def _clear_cell():
    sfx = state.sfx_patches[state.se_sfx_id]
    sfx["notes"][state.se_cell_x] = (sfx_data.NOTE_EMPTY, 0, 0, 0)

def sfx_editor_update():
    _ensure_audio_state()
    sfx = state.sfx_patches[state.se_sfx_id]
    mx, my = state.mouse_x, state.mouse_y

    # Maus: Zelle waehlen
    grid_w = SE_CELL_W * sfx_data.NOTES_PER_SFX
    grid_h = SE_CELL_H * SE_ROWS
    if mouse_btnp(0) and _in_rect(mx, my, SE_GRID_X, SE_GRID_Y, grid_w, grid_h):
        state.se_cell_x = (mx - SE_GRID_X) // SE_CELL_W
        state.se_cell_y = (my - SE_GRID_Y) // SE_CELL_H

    # Maus-Rad / Rechtsklick: Wert hoch/runter
    if mouse_btn(2) and _in_rect(mx, my, SE_GRID_X, SE_GRID_Y, grid_w, grid_h):
        if mouse_btnp(2):
            _clear_cell()

    # Pfeiltasten: Cursor bewegen
    if btnp('left'):  state.se_cell_x = max(0, state.se_cell_x - 1)
    if btnp('right'): state.se_cell_x = min(31, state.se_cell_x + 1)
    if btnp('up'):
        if btn('shift'):
            _change_cell_value(+1)    # Shift+Up: Wert erhoehen
        else:
            state.se_cell_y = max(0, state.se_cell_y - 1)
    if btnp('down'):
        if btn('shift'):
            _change_cell_value(-1)
        else:
            state.se_cell_y = min(SE_ROWS - 1, state.se_cell_y + 1)

    # +/- aendern Wert (bequemer als Shift+Pfeil)
    for k in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            _change_cell_value(+1)
    for k in (pygame.K_MINUS, pygame.K_KP_MINUS):
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            _change_cell_value(-1)

    # SFX-Slot wechseln mit Komma/Punkt
    if state.keys.get(pygame.K_COMMA, False) and not state.keys_prev.get(pygame.K_COMMA, False):
        state.se_sfx_id = (state.se_sfx_id - 1) % sfx_data.NUM_SFX
    if state.keys.get(pygame.K_PERIOD, False) and not state.keys_prev.get(pygame.K_PERIOD, False):
        state.se_sfx_id = (state.se_sfx_id + 1) % sfx_data.NUM_SFX

    # Speed mit [ ]
    if state.keys.get(pygame.K_LEFTBRACKET, False) and not state.keys_prev.get(pygame.K_LEFTBRACKET, False):
        sfx["speed"] = max(1, sfx["speed"] - 1)
    if state.keys.get(pygame.K_RIGHTBRACKET, False) and not state.keys_prev.get(pygame.K_RIGHTBRACKET, False):
        sfx["speed"] = min(32, sfx["speed"] + 1)

    # Space: SFX abspielen
    if btnp('space'):
        tracker.sfx(state.se_sfx_id, channel=7)

    # Klavier-Tasten
    _piano_input()

def sfx_editor_draw():
    cls(0)
    sfx = state.sfx_patches[state.se_sfx_id]
    rectfill(0, 0, WIDTH, 9, 1)
    text(f"SFX EDIT  ID:{state.se_sfx_id:02d}  SPEED:{sfx['speed']:02d}  "
         f"LOOP:{sfx['loop_start']:02d}-{sfx['loop_end']:02d}",
         2, 2, 7)

    # Spaltenkoepfe (Notennummern alle 4)
    for col in range(0, sfx_data.NOTES_PER_SFX, 4):
        text(f"{col:02}", SE_GRID_X + col * SE_CELL_W, SE_GRID_Y - 8, 6)

    # Reihen-Labels
    row_labels = ["NOT", "INS", "VOL", "FX "]
    for r, lbl in enumerate(row_labels):
        text(lbl, SE_GRID_X - 18, SE_GRID_Y + r * SE_CELL_H + 1, 6)

    # Notenraster
    for col in range(sfx_data.NOTES_PER_SFX):
        note, inst, vol, fx = sfx["notes"][col]
        x = SE_GRID_X + col * SE_CELL_W
        # Hintergrund: alle 4 Spalten dezent abheben
        if col % 4 == 0:
            rectfill(x, SE_GRID_Y, SE_CELL_W, SE_CELL_H * SE_ROWS, 1)

        # Note-Reihe: Note-Name oder ---
        col_color = 7 if note != sfx_data.NOTE_EMPTY else 5
        nname = sfx_data.note_name(note) if note != sfx_data.NOTE_EMPTY else "-"
        text(nname[:2], x + 1, SE_GRID_Y + 1, col_color)

        # Instrument-Reihe
        if note != sfx_data.NOTE_EMPTY:
            text(sfx_data.INSTRUMENT_NAMES[inst][:2],
                 x + 1, SE_GRID_Y + SE_CELL_H + 1,
                 [11, 12, 9, 8, 14, 13, 10, 15][inst])

            # Volume als senkrechter Balken (besser sichtbar)
            bar_h = max(1, vol)
            rectfill(x + 2, SE_GRID_Y + 2 * SE_CELL_H + (7 - bar_h),
                     3, bar_h, 11)

            # Effekt
            if fx != 0:
                text(sfx_data.EFFECT_NAMES[fx][:2],
                     x + 1, SE_GRID_Y + 3 * SE_CELL_H + 1, 14)

    # Cursor-Markierung
    cur_x = SE_GRID_X + state.se_cell_x * SE_CELL_W
    cur_y = SE_GRID_Y + state.se_cell_y * SE_CELL_H
    rect(cur_x - 1, cur_y - 1, SE_CELL_W + 1, SE_CELL_H + 1, 8)

    # Loop-Marker
    if sfx["loop_end"] > sfx["loop_start"]:
        ls_x = SE_GRID_X + sfx["loop_start"] * SE_CELL_W
        le_x = SE_GRID_X + sfx["loop_end"] * SE_CELL_W
        line(ls_x, SE_GRID_Y - 1, ls_x, SE_GRID_Y + SE_CELL_H * SE_ROWS, 11)
        line(le_x, SE_GRID_Y - 1, le_x, SE_GRID_Y + SE_CELL_H * SE_ROWS, 11)

    # Detail-Anzeige aktuelle Zelle
    note, inst, vol, fx = sfx["notes"][state.se_cell_x]
    info_y = SE_GRID_Y + SE_ROWS * SE_CELL_H + 6
    text(f"CELL:{state.se_cell_x:02}  NOTE:{sfx_data.note_name(note)}  "
         f"INST:{sfx_data.INSTRUMENT_NAMES[inst]}  VOL:{vol}  "
         f"FX:{sfx_data.EFFECT_NAMES[fx]}", 4, info_y, 7)

    # Klavier-Hilfe
    text("KLAVIER  ZSXDCVGBHNJM = OKTAVE 3", 4, info_y + 10, 6)
    text("         QWERTY... = OKTAVE 4",    4, info_y + 18, 6)

    # Instrument-Legende
    text("INSTRUMENTE:", 4, 110, 6)
    for i in range(8):
        col_pal = [11, 12, 9, 8, 14, 13, 10, 15][i]
        text(f"{i}:{sfx_data.INSTRUMENT_NAMES[i]}",
             4 + (i % 4) * 32, 118 + (i // 4) * 8, col_pal)

    # Effekt-Legende
    text("EFFEKTE:", 4, 138, 6)
    fx_help = ["NONE", "SLIDE", "VIBRATO", "DROP",
               "FADE-IN", "FADE-OUT", "ARPEGGIO FAST", "ARP SLOW"]
    for i in range(8):
        text(f"{i}:{fx_help[i]}",
             4 + (i % 2) * 100, 146 + (i // 2) * 8, 14 if i > 0 else 5)

    # Steuerung-Hilfe
    text("PFEILE NAV  +/- WERT  SPACE PLAY",  4, 184, 7)
    text(",/. SLOT   BRACKETS SPEED  RMB CLR", 4, 192, 7)
    text("F4 MUSIC  F5 SAVE  F8 LOAD  ESC",   4, 210, 7)

# ----------------------------------------------------------------------
# MUSIC-EDITOR
# ----------------------------------------------------------------------

ME_TRACK_X = 4
ME_TRACK_Y = 22
ME_TRACK_CELL = 12
ME_TRACK_LEN = 16

ME_PAT_X = 4
ME_PAT_Y = 70
ME_PAT_CELL_W = 28
ME_PAT_CELL_H = 12

def music_editor_update():
    _ensure_audio_state()
    mx, my = state.mouse_x, state.mouse_y

    # Track-Bereich: Pattern-Slot waehlen
    track = state.music_tracks[state.me_track_id]
    track_w = ME_TRACK_CELL * ME_TRACK_LEN
    if mouse_btnp(0) and _in_rect(mx, my, ME_TRACK_X, ME_TRACK_Y,
                                  track_w, ME_TRACK_CELL):
        state.me_cursor = (mx - ME_TRACK_X) // ME_TRACK_CELL
        state.me_focus = "track"

    # Pattern-Bereich: Kanal waehlen
    pat_w = ME_PAT_CELL_W * sfx_data.CHANNELS_PER_PAT
    pat_h = ME_PAT_CELL_H
    if mouse_btnp(0) and _in_rect(mx, my, ME_PAT_X, ME_PAT_Y, pat_w, pat_h):
        state.me_pat_chan = (mx - ME_PAT_X) // ME_PAT_CELL_W
        state.me_focus = "pattern"

    # Track-Slot wechseln
    if btnp('a'): state.me_track_id = (state.me_track_id - 1) % sfx_data.NUM_TRACKS
    if btnp('s'): state.me_track_id = (state.me_track_id + 1) % sfx_data.NUM_TRACKS

    # Pattern-Slot mit ,/.
    if state.keys.get(pygame.K_COMMA, False) and not state.keys_prev.get(pygame.K_COMMA, False):
        state.me_pattern_id = (state.me_pattern_id - 1) % sfx_data.NUM_PATTERNS
    if state.keys.get(pygame.K_PERIOD, False) and not state.keys_prev.get(pygame.K_PERIOD, False):
        state.me_pattern_id = (state.me_pattern_id + 1) % sfx_data.NUM_PATTERNS

    # Pfeile: Werte aendern je nach Fokus
    if state.me_focus == "track":
        if btnp('left'):  state.me_cursor = max(0, state.me_cursor - 1)
        if btnp('right'): state.me_cursor = min(ME_TRACK_LEN - 1, state.me_cursor + 1)
        # Up/Down aendert Pattern-ID an Cursor-Position
        while len(track) <= state.me_cursor:
            track.append(0)
        if btnp('up'):
            track[state.me_cursor] = (track[state.me_cursor] + 1) % sfx_data.NUM_PATTERNS
        if btnp('down'):
            track[state.me_cursor] = (track[state.me_cursor] - 1) % sfx_data.NUM_PATTERNS
        # Delete: Eintrag entfernen
        for k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            if state.keys.get(k, False) and not state.keys_prev.get(k, False):
                if state.me_cursor < len(track):
                    del track[state.me_cursor]
                    state.me_cursor = max(0, min(state.me_cursor, len(track)))

    elif state.me_focus == "pattern":
        pat = state.music_patterns[state.me_pattern_id]
        # Up/Down aendert SFX-ID im aktuellen Kanal
        chan = state.me_pat_chan
        cur_val = pat["channels"][chan]
        if btnp('up'):
            if cur_val == sfx_data.SFX_EMPTY:
                pat["channels"][chan] = 0
            else:
                pat["channels"][chan] = (cur_val + 1) % sfx_data.NUM_SFX
        if btnp('down'):
            if cur_val == sfx_data.SFX_EMPTY:
                pat["channels"][chan] = sfx_data.NUM_SFX - 1
            else:
                pat["channels"][chan] = (cur_val - 1) % sfx_data.NUM_SFX
        if btnp('left'):
            state.me_pat_chan = (state.me_pat_chan - 1) % sfx_data.CHANNELS_PER_PAT
        if btnp('right'):
            state.me_pat_chan = (state.me_pat_chan + 1) % sfx_data.CHANNELS_PER_PAT
        # X = Kanal leeren
        if state.keys.get(pygame.K_x, False) and not state.keys_prev.get(pygame.K_x, False):
            pat["channels"][chan] = sfx_data.SFX_EMPTY

    # TAB wechselt Fokus
    if state.keys.get(pygame.K_TAB, False) and not state.keys_prev.get(pygame.K_TAB, False):
        state.me_focus = "pattern" if state.me_focus == "track" else "track"

    # Space: Track abspielen, Enter: nur Pattern
    if btnp('space'):
        tracker.music(state.me_track_id)
    if btnp('enter'):
        tracker._start_pattern(state.me_pattern_id)

def music_editor_draw():
    cls(0)
    rectfill(0, 0, WIDTH, 9, 1)
    text(f"MUSIC EDIT  TRACK:{state.me_track_id}  "
         f"PATTERN:{state.me_pattern_id:02d}  FOCUS:{state.me_focus.upper()}",
         2, 2, 7)

    # Track-Sequenz
    text("TRACK:", 4, ME_TRACK_Y - 9, 6)
    track = state.music_tracks[state.me_track_id]
    for i in range(ME_TRACK_LEN):
        x = ME_TRACK_X + i * ME_TRACK_CELL
        rectfill(x, ME_TRACK_Y, ME_TRACK_CELL - 1, ME_TRACK_CELL, 1)
        if i < len(track):
            text(f"{track[i]:02}", x + 1, ME_TRACK_Y + 3, 11)
        else:
            text("--", x + 1, ME_TRACK_Y + 3, 5)
    # Cursor im Track
    if state.me_focus == "track":
        cx = ME_TRACK_X + state.me_cursor * ME_TRACK_CELL
        rect(cx - 1, ME_TRACK_Y - 1, ME_TRACK_CELL, ME_TRACK_CELL + 1, 8)

    # Pattern-Editor
    text(f"PATTERN {state.me_pattern_id:02d}:", 4, ME_PAT_Y - 9, 6)
    pat = state.music_patterns[state.me_pattern_id]
    for ch in range(sfx_data.CHANNELS_PER_PAT):
        x = ME_PAT_X + ch * ME_PAT_CELL_W
        rectfill(x, ME_PAT_Y, ME_PAT_CELL_W - 2, ME_PAT_CELL_H, 1)
        text(f"CH{ch}", x + 2, ME_PAT_Y + 1, 6)
        sfx_id = pat["channels"][ch]
        if sfx_id == sfx_data.SFX_EMPTY:
            text("---", x + 14, ME_PAT_Y + 4, 5)
        else:
            text(f"S{sfx_id:02}", x + 14, ME_PAT_Y + 4, 12)
    if state.me_focus == "pattern":
        cx = ME_PAT_X + state.me_pat_chan * ME_PAT_CELL_W
        rect(cx - 1, ME_PAT_Y - 1, ME_PAT_CELL_W - 1, ME_PAT_CELL_H + 1, 8)

    # Live-Status: laeuft Music gerade?
    if state.music_playing:
        mp = state.music_playing
        text(f"PLAYING  T:{mp['track_id']}  STEP:{mp['pattern_seq']}",
             4, 110, 11)
    else:
        text("STOPPED", 4, 110, 5)

    # Hilfe
    text("TAB FOKUS  PFEILE NAV/WERT", 4, 170, 7)
    text("A/S TRACK  ,/. PATTERN", 4, 178, 7)
    text("SPACE PLAY  ENTER PAT  X CLEAR", 4, 186, 7)
    text("F3 SFX F5 SAVE F8 LOAD ESC ZURK", 4, 210, 7)

# ----------------------------------------------------------------------
# SCHALTER
# ----------------------------------------------------------------------

def toggle(mode):
    _ensure_audio_state()
    state.editor_mode = None if state.editor_mode == mode else mode
