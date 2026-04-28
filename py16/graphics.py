"""
py16.graphics
=============
2D-Zeichenfunktionen, Kamera, Clipping, Palette-Tools und Text-Renderer.
"""

import pygame

from . import state
from .core import WIDTH, HEIGHT, PALETTE, color_rgb

# ======================================================================
# FONT (3x5 Pixel)
# ======================================================================

_FONT_DATA = {
    'A':"010101111101101", 'B':"110101110101110", 'C':"011100100100011",
    'D':"110101101101110", 'E':"111100111100111", 'F':"111100111100100",
    'G':"011100101101011", 'H':"101101111101101", 'I':"111010010010111",
    'J':"111010010101010", 'K':"101101110101101", 'L':"100100100100111",
    'M':"101111101101101", 'N':"110101101101101", 'O':"010101101101010",
    'P':"110101110100100", 'Q':"010101101110011", 'R':"110101110101101",
    'S':"011100010001110", 'T':"111010010010010", 'U':"101101101101011",
    'V':"101101101101010", 'W':"101101101111101", 'X':"101101010101101",
    'Y':"101101010010010", 'Z':"111001010100111",
    '0':"010101101101010", '1':"010110010010111", '2':"110001010100111",
    '3':"110001011001110", '4':"101101111001001", '5':"111100110001110",
    '6':"011100111101011", '7':"111001010100100", '8':"010101010101010",
    '9':"010101111001011", ' ':"000000000000000", '.':"000000000000010",
    '!':"010010010000010", '?':"110001010000010", '-':"000000111000000",
    '+':"000010111010000", ':':"000010000010000", ',':"000000000010100",
    '/':"001001010100100",
    # Programmier-Sonderzeichen
    '(':"010100100100010", ')':"010001001001010",
    '[':"011010010010011", ']':"110010010010110",
    '{':"011010110010011", '}':"110010011010110",
    '<':"001010100010001", '>':"100010001010100",
    '=':"000111000111000", '*':"000101010101000",
    '#':"101111101111101", '@':"010101111100011",
    '_':"000000000000111", '&':"110100110101011",
    '|':"010010010010010", '\\':"100100010001001",
    '"':"101101000000000", "'":"010010000000000",
    '`':"010100000000000", ';':"000010000010100",
    '%':"101001010100101", '~':"000001111100000",
    '^':"010101000000000", '$':"011110010011110",
}

# ======================================================================
# KAMERA & CLIPPING
# ======================================================================

def camera(x=0, y=0):
    state.cam_x = int(x)
    state.cam_y = int(y)

def clip(x=None, y=None, w=None, h=None):
    """Scissor-Rechteck. Ohne Argumente: zuruecksetzen."""
    if x is None:
        state.clip_rect = None
        state.screen.set_clip(None)
    else:
        state.clip_rect = (int(x), int(y), int(w), int(h))
        state.screen.set_clip(state.clip_rect)

# ======================================================================
# GRUNDFORMEN
# ======================================================================

def cls(color_index=0):
    state.screen.fill(color_rgb(color_index))

def pset(x, y, color_index):
    sx, sy = int(x - state.cam_x), int(y - state.cam_y)
    if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
        state.screen.set_at((sx, sy), color_rgb(color_index))

def pget(x, y):
    """Liefert den Paletten-Index der Farbe an (x,y)."""
    sx, sy = int(x - state.cam_x), int(y - state.cam_y)
    if not (0 <= sx < WIDTH and 0 <= sy < HEIGHT):
        return 0
    r, g, b = state.screen.get_at((sx, sy))[:3]
    best, bd = 0, 1 << 30
    for i, (pr, pg, pb) in enumerate(PALETTE):
        d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
        if d < bd:
            bd, best = d, i
    return best

def rectfill(x, y, w, h, color_index):
    pygame.draw.rect(state.screen, color_rgb(color_index),
                     (x - state.cam_x, y - state.cam_y, w, h))

def rect(x, y, w, h, color_index):
    pygame.draw.rect(state.screen, color_rgb(color_index),
                     (x - state.cam_x, y - state.cam_y, w, h), 1)

def line(x0, y0, x1, y1, color_index):
    pygame.draw.line(state.screen, color_rgb(color_index),
                     (x0 - state.cam_x, y0 - state.cam_y),
                     (x1 - state.cam_x, y1 - state.cam_y))

def circ(x, y, r, color_index):
    if r > 0:
        pygame.draw.circle(state.screen, color_rgb(color_index),
                           (int(x - state.cam_x), int(y - state.cam_y)),
                           int(r), 1)

def circfill(x, y, r, color_index):
    if r > 0:
        pygame.draw.circle(state.screen, color_rgb(color_index),
                           (int(x - state.cam_x), int(y - state.cam_y)),
                           int(r))

# ======================================================================
# TEXT (mit Font-Cache)
# ======================================================================

def _build_char_surface(char, color_idx):
    surf = pygame.Surface((3, 5))
    surf.set_colorkey((0, 0, 0))
    bits = _FONT_DATA.get(char, _FONT_DATA['?'])
    col = color_rgb(color_idx)
    for i, b in enumerate(bits):
        if b == '1':
            surf.set_at((i % 3, i // 3), col)
    return surf

def text(string, x, y, color_index=7, upper=True):
    """Zeichnet Text. Wenn upper=True: Eingabe wird automatisch
    .upper() umgesetzt (Default fuer alle UI-Elemente).
    Wenn upper=False: Kleinbuchstaben werden auf das Grossbuchstaben-
    Glyph gemappt, da der 3x5-Font keine echten Kleinbuchstaben hat
    - aber der String selbst bleibt unveraendert (wichtig fuer
    Cursor-Positionierung im Code-Editor)."""
    s = str(string)
    if upper:
        s = s.upper()
    px, py = x, y
    for char in s:
        if char == '\n':
            py += 6
            px = x
            continue
        # Kleinbuchstaben auf Grossbuchstaben fallback
        glyph_char = char
        if not upper and 'a' <= char <= 'z':
            glyph_char = char.upper()
        key = (glyph_char, color_index & 0xFF)
        if key not in state.font_cache:
            state.font_cache[key] = _build_char_surface(glyph_char, color_index)
        state.screen.blit(state.font_cache[key],
                          (px - state.cam_x, py - state.cam_y))
        px += 4

# ======================================================================
# PALETTEN-MANIPULATION
# ======================================================================

def pal(c0=None, c1=None):
    """pal()         -> reset
       pal(c0, c1)   -> Index c0 wird als c1 dargestellt."""
    if c0 is None:
        state.pal_remap = list(range(256))
    else:
        state.pal_remap[c0 & 0xFF] = c1 & 0xFF
    state.font_cache.clear()

def palt(color_index=None, transparent=True):
    """palt()              -> reset (nur 0 transparent)
       palt(idx, True/False)"""
    if color_index is None:
        state.transparent = {0}
    else:
        if transparent:
            state.transparent.add(color_index & 0xFF)
        else:
            state.transparent.discard(color_index & 0xFF)
    if state.transparent:
        first = next(iter(state.transparent))
        state.sprite_sheet.set_colorkey(PALETTE[first])
    else:
        state.sprite_sheet.set_colorkey(None)
