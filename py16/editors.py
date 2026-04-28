"""
py16.editors
============
Eingebaute Editoren fuer Sprites (F1) und Map (F2). Auswahl per Maus,
Flag-Toggle per Zifferntasten 0-7.
"""

import pygame

from . import state
from .core import (PALETTE, WIDTH, HEIGHT, SHEET_SIZE,
                   SPRITES_PER_ROW, SPRITE_PIX, MAP_W, MAP_H)
from .graphics import (cls, rectfill, rect, line, text)
from .sprites import sset, spr
from .maps import mset, draw_map, fset, fget
from .input import btn, btnp, mouse_btn, mouse_btnp

# ======================================================================
# HELFER
# ======================================================================

def _box(x, y, w, h, fill, border):
    rectfill(x, y, w, h, fill)
    rect(x, y, w, h, border)

def _in_rect(mx, my, x, y, w, h):
    return x <= mx < x + w and y <= my < y + h

# ======================================================================
# SPRITE-EDITOR
# ======================================================================

# Layout
SE_CANVAS_X, SE_CANVAS_Y, SE_CANVAS_PIX = 4, 12, 10     # 8*10 = 80
SE_PAL_X,    SE_PAL_Y,    SE_PAL_SLOT   = 90, 12, 4     # 16*4 = 64
SE_SHEET_X,  SE_SHEET_Y,  SE_SHEET_SCALE = 160, 12, 0.25  # 64x64

def sprite_editor_update():
    mx, my = state.mouse_x, state.mouse_y

    # Canvas: malen (links) oder loeschen (rechts)
    if mouse_btn(0) or mouse_btn(2):
        if _in_rect(mx, my, SE_CANVAS_X, SE_CANVAS_Y,
                    8 * SE_CANVAS_PIX, 8 * SE_CANVAS_PIX):
            px = (mx - SE_CANVAS_X) // SE_CANVAS_PIX
            py = (my - SE_CANVAS_Y) // SE_CANVAS_PIX
            sx = (state.edit_sprite % SPRITES_PER_ROW) * SPRITE_PIX + px
            sy = (state.edit_sprite // SPRITES_PER_ROW) * SPRITE_PIX + py
            color = state.edit_color if mouse_btn(0) else 0
            sset(sx, sy, color)

    # Palette
    if mouse_btnp(0) and _in_rect(mx, my, SE_PAL_X, SE_PAL_Y,
                                  16 * SE_PAL_SLOT, 16 * SE_PAL_SLOT):
        cx = (mx - SE_PAL_X) // SE_PAL_SLOT
        cy = (my - SE_PAL_Y) // SE_PAL_SLOT
        state.edit_color = cy * 16 + cx

    # Sheet-Uebersicht
    sheet_w = int(SHEET_SIZE * SE_SHEET_SCALE)
    if mouse_btnp(0) and _in_rect(mx, my, SE_SHEET_X, SE_SHEET_Y,
                                  sheet_w, sheet_w):
        rel_x = (mx - SE_SHEET_X) / SE_SHEET_SCALE
        rel_y = (my - SE_SHEET_Y) / SE_SHEET_SCALE
        cx = int(rel_x // SPRITE_PIX)
        cy = int(rel_y // SPRITE_PIX)
        state.edit_sprite = cy * SPRITES_PER_ROW + cx

    # Tastatur
    if btnp('left'):
        state.edit_sprite = (state.edit_sprite - 1) % 1024
    if btnp('right'):
        state.edit_sprite = (state.edit_sprite + 1) % 1024
    if btnp('up'):
        state.edit_sprite = (state.edit_sprite - SPRITES_PER_ROW) % 1024
    if btnp('down'):
        state.edit_sprite = (state.edit_sprite + SPRITES_PER_ROW) % 1024
    for i in range(8):
        k = pygame.K_0 + i
        if state.keys.get(k, False) and not state.keys_prev.get(k, False):
            fset(state.edit_sprite, i, not fget(state.edit_sprite, i))

def sprite_editor_draw():
    cls(0)
    rectfill(0, 0, WIDTH, 9, 1)
    flags = state.sprite_flags[state.edit_sprite]
    flag_str = ''.join('1' if flags & (1 << i) else '0' for i in range(8))
    text(f"SPR EDIT  ID:{state.edit_sprite:03d}  FLG:{flag_str}", 2, 2, 7)

    # Canvas
    _box(SE_CANVAS_X - 1, SE_CANVAS_Y - 1,
         8 * SE_CANVAS_PIX + 2, 8 * SE_CANVAS_PIX + 2, 0, 6)
    sx0 = (state.edit_sprite % SPRITES_PER_ROW) * SPRITE_PIX
    sy0 = (state.edit_sprite // SPRITES_PER_ROW) * SPRITE_PIX
    for py in range(8):
        for px in range(8):
            rgb = state.sprite_sheet.get_at((sx0 + px, sy0 + py))[:3]
            best, bd = 0, 1 << 30
            for i, p in enumerate(PALETTE):
                d = (rgb[0]-p[0])**2 + (rgb[1]-p[1])**2 + (rgb[2]-p[2])**2
                if d < bd:
                    bd, best = d, i
            if best != 0:
                rectfill(SE_CANVAS_X + px * SE_CANVAS_PIX,
                         SE_CANVAS_Y + py * SE_CANVAS_PIX,
                         SE_CANVAS_PIX, SE_CANVAS_PIX, best)
            rect(SE_CANVAS_X + px * SE_CANVAS_PIX,
                 SE_CANVAS_Y + py * SE_CANVAS_PIX,
                 SE_CANVAS_PIX, SE_CANVAS_PIX, 1)

    # Palette
    _box(SE_PAL_X - 1, SE_PAL_Y - 1,
         16 * SE_PAL_SLOT + 2, 16 * SE_PAL_SLOT + 2, 0, 6)
    for cy in range(16):
        for cx in range(16):
            rectfill(SE_PAL_X + cx * SE_PAL_SLOT,
                     SE_PAL_Y + cy * SE_PAL_SLOT,
                     SE_PAL_SLOT, SE_PAL_SLOT, cy * 16 + cx)
    cy, cx = divmod(state.edit_color, 16)
    rect(SE_PAL_X + cx * SE_PAL_SLOT - 1,
         SE_PAL_Y + cy * SE_PAL_SLOT - 1,
         SE_PAL_SLOT + 2, SE_PAL_SLOT + 2, 7)
    text(f"COL:{state.edit_color:03d}",
         SE_PAL_X, SE_PAL_Y + 16 * SE_PAL_SLOT + 2, 6)

    # Sheet-Uebersicht
    sheet_w = int(SHEET_SIZE * SE_SHEET_SCALE)
    _box(SE_SHEET_X - 1, SE_SHEET_Y - 1, sheet_w + 2, sheet_w + 2, 0, 6)
    scaled = pygame.transform.scale(state.sprite_sheet, (sheet_w, sheet_w))
    state.screen.blit(scaled, (SE_SHEET_X, SE_SHEET_Y))
    cur_x = SE_SHEET_X + int((state.edit_sprite % SPRITES_PER_ROW) * SPRITE_PIX * SE_SHEET_SCALE)
    cur_y = SE_SHEET_Y + int((state.edit_sprite // SPRITES_PER_ROW) * SPRITE_PIX * SE_SHEET_SCALE)
    cur_s = max(2, int(SPRITE_PIX * SE_SHEET_SCALE))
    rect(cur_x, cur_y, cur_s, cur_s, 8)

    # Hilfe
    text("LMB PAINT  RMB ERASE",  90, 84,  6)
    text("PFEILE WECHSELN SPR",   90, 92,  6)
    text("0-7 FLAG TOGGLE",       90, 100, 6)
    text("F2 MAP F5 SAVE F8 LOAD", 4, 210, 7)
    text("ESC ZURUECK",           160, 210, 7)

# ======================================================================
# MAP-EDITOR
# ======================================================================

ME_MAP_X, ME_MAP_Y       = 0, 12
ME_MAP_TILES_W           = 32
ME_MAP_TILES_H           = 16
ME_PICK_X, ME_PICK_Y     = 0, 144
ME_PICK_W, ME_PICK_H     = 256, 64
ME_PICK_TILES_PER_PAGE   = 256

def map_editor_update():
    mx, my = state.mouse_x, state.mouse_y

    if (mouse_btn(0) or mouse_btn(2)) and _in_rect(
            mx, my, ME_MAP_X, ME_MAP_Y,
            ME_MAP_TILES_W * 8, ME_MAP_TILES_H * 8):
        cx = state.edit_map_cam[0] + (mx - ME_MAP_X) // 8
        cy = state.edit_map_cam[1] + (my - ME_MAP_Y) // 8
        if 0 <= cx < MAP_W and 0 <= cy < MAP_H:
            mset(cx, cy, state.edit_tile if mouse_btn(0) else 0)

    if mouse_btnp(0) and _in_rect(mx, my, ME_PICK_X, ME_PICK_Y,
                                  ME_PICK_W, ME_PICK_H):
        cx = (mx - ME_PICK_X) // 8
        cy = (my - ME_PICK_Y) // 8
        state.edit_tile = (state.edit_picker_page * ME_PICK_TILES_PER_PAGE
                           + cy * SPRITES_PER_ROW + cx)

    speed = 4 if btn('shift') else 1
    if btn('left'):
        state.edit_map_cam[0] = max(0, state.edit_map_cam[0] - speed)
    if btn('right'):
        state.edit_map_cam[0] = min(MAP_W - ME_MAP_TILES_W,
                                    state.edit_map_cam[0] + speed)
    if btn('up'):
        state.edit_map_cam[1] = max(0, state.edit_map_cam[1] - speed)
    if btn('down'):
        state.edit_map_cam[1] = min(MAP_H - ME_MAP_TILES_H,
                                    state.edit_map_cam[1] + speed)

    if btnp('a'): state.edit_picker_page = (state.edit_picker_page - 1) % 4
    if btnp('s'): state.edit_picker_page = (state.edit_picker_page + 1) % 4

def map_editor_draw():
    from .graphics import camera
    cls(0)
    rectfill(0, 0, WIDTH, 9, 1)
    text(f"MAP EDIT  CAM:{state.edit_map_cam[0]:03d},"
         f"{state.edit_map_cam[1]:03d}  TILE:{state.edit_tile:04d}",
         2, 2, 7)

    saved_cam = (state.cam_x, state.cam_y)
    camera(state.edit_map_cam[0] * 8 - ME_MAP_X,
           state.edit_map_cam[1] * 8 - ME_MAP_Y)
    draw_map(state.edit_map_cam[0], state.edit_map_cam[1],
             state.edit_map_cam[0] * 8, state.edit_map_cam[1] * 8,
             ME_MAP_TILES_W, ME_MAP_TILES_H)
    camera(*saved_cam)

    # Gitter alle 4 Tiles
    for i in range(0, ME_MAP_TILES_W + 1, 4):
        line(ME_MAP_X + i * 8, ME_MAP_Y,
             ME_MAP_X + i * 8, ME_MAP_Y + ME_MAP_TILES_H * 8, 1)
    for j in range(0, ME_MAP_TILES_H + 1, 4):
        line(ME_MAP_X, ME_MAP_Y + j * 8,
             ME_MAP_X + ME_MAP_TILES_W * 8, ME_MAP_Y + j * 8, 1)

    # Cursor
    if _in_rect(state.mouse_x, state.mouse_y, ME_MAP_X, ME_MAP_Y,
                ME_MAP_TILES_W * 8, ME_MAP_TILES_H * 8):
        cx = (state.mouse_x - ME_MAP_X) // 8
        cy = (state.mouse_y - ME_MAP_Y) // 8
        rect(ME_MAP_X + cx * 8, ME_MAP_Y + cy * 8, 8, 8, 7)

    # Trennlinie und Picker
    rectfill(0, 140, WIDTH, 4, 1)
    text(f"PAGE {state.edit_picker_page+1}/4  A/S", 2, 141, 7)

    base = state.edit_picker_page * ME_PICK_TILES_PER_PAGE
    for i in range(ME_PICK_TILES_PER_PAGE):
        sid = base + i
        if sid >= 1024: break
        cx = i % SPRITES_PER_ROW
        cy = i // SPRITES_PER_ROW
        spr(sid, ME_PICK_X + cx * 8, ME_PICK_Y + cy * 8)

    if base <= state.edit_tile < base + ME_PICK_TILES_PER_PAGE:
        local = state.edit_tile - base
        cx = local % SPRITES_PER_ROW
        cy = local // SPRITES_PER_ROW
        rect(ME_PICK_X + cx * 8 - 1, ME_PICK_Y + cy * 8 - 1, 10, 10, 8)

    text("LMB SETZEN RMB LOESCHEN", 4, 210, 7)
    text("F1 SPR  F5 SAVE  F8 LOAD  ESC", 4, 217, 7)

# ======================================================================
# SCHALTER
# ======================================================================

def toggle(mode):
    state.editor_mode = None if state.editor_mode == mode else mode
