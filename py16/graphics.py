"""
py16.graphics
=============
2D drawing functions, camera, clipping, palette tools, and text renderer.
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
    """Set the camera offset for the active viewport.

    The cart says "look at world position (x, y) - put it at the top-left
    of the visible area". With splitscreen viewports, the engine adjusts
    this internally so the same camera works regardless of which viewport
    you're rendering into.
    """
    # The user-facing camera (state.cam_x/y) gets the viewport offset
    # baked in, so all draw operations (which subtract cam from world
    # to get screen coords) automatically land inside the viewport.
    viewport_clip = getattr(state, "viewport_clip", None)
    if viewport_clip is None:
        state.cam_x = int(x)
        state.cam_y = int(y)
    else:
        # Subtract the viewport's top-left so that world (x, y) shows up
        # at the viewport's (0, 0) - which on screen is (vp_x, vp_y).
        state.cam_x = int(x) - viewport_clip[0]
        state.cam_y = int(y) - viewport_clip[1]

def clip(x=None, y=None, w=None, h=None):
    """Scissor rect inside the current viewport. Without arguments:
    reset to the viewport bounds (or whole screen if no viewport)."""
    viewport_clip = getattr(state, "viewport_clip", None)
    if x is None:
        # Reset: fall back to viewport clip if any, else full screen
        state.clip_rect = None
        state.screen.set_clip(viewport_clip)
    else:
        # Combine user clip with viewport clip via rect intersection
        user_rect = pygame.Rect(int(x), int(y), int(w), int(h))
        if viewport_clip is not None:
            vp = pygame.Rect(*viewport_clip)
            user_rect = user_rect.clip(vp)
        state.clip_rect = (user_rect.x, user_rect.y,
                           user_rect.w, user_rect.h)
        state.screen.set_clip(state.clip_rect)

# ======================================================================
# BLENDING
# ======================================================================

def blend_mode(mode="normal", alpha=128):
    """Set the global blending mode for subsequent draw operations.

    mode:
      "normal" : default, no blending (back-compat)
      "add"    : additive (pixel + drawn = brighter)  -- glow, plasma, fire
      "sub"    : subtractive (pixel - drawn = darker) -- shadows, eclipse
      "alpha"  : alpha blend (pixel * (1-a) + drawn * a) -- ghosts, water

    alpha : 0..255, only used by "alpha" mode (default 128 = 50%)
    """
    if mode not in ("normal", "add", "sub", "alpha"):
        return
    state.blend_mode = mode
    state.blend_alpha = max(0, min(255, int(alpha)))

def _blend_flag():
    """Returns the pygame.BLEND_* flag for the current state.blend_mode,
    or 0 for normal."""
    m = getattr(state, "blend_mode", "normal")
    if m == "add":
        return pygame.BLEND_RGBA_ADD
    if m == "sub":
        return pygame.BLEND_RGBA_SUB
    return 0    # normal or alpha (alpha handled via set_alpha on surface)

# Module-level cache of throwaway surfaces by size, to avoid repeated
# allocation in the hot path. Pygame surface alloc is slow.
_blend_scratch = {}

def _scratch_surface(w, h):
    """Get a reusable scratch RGB surface of the given size."""
    key = (w, h)
    if key not in _blend_scratch:
        _blend_scratch[key] = pygame.Surface((w, h)).convert()
    return _blend_scratch[key]

def _blend_fill_rect(x, y, w, h, color_index):
    """Draw a filled rect using the current blend mode."""
    m = getattr(state, "blend_mode", "normal")
    if m == "normal":
        pygame.draw.rect(state.screen, color_rgb(color_index),
                         (x - state.cam_x, y - state.cam_y, w, h))
        return
    if w <= 0 or h <= 0:
        return
    tmp = _scratch_surface(w, h)
    tmp.fill(color_rgb(color_index))
    if m == "alpha":
        tmp.set_alpha(state.blend_alpha)
        flag = 0
    else:
        tmp.set_alpha(255)
        flag = _blend_flag()
    state.screen.blit(tmp, (x - state.cam_x, y - state.cam_y),
                      special_flags=flag)

def cls(color_index=0):
    """Clear the screen (or active viewport) to the given color."""
    viewport_clip = getattr(state, "viewport_clip", None)
    if viewport_clip is None:
        # Full-screen clear, fastest path
        state.screen.fill(color_rgb(color_index))
    else:
        # Viewport-scoped clear - use draw.rect so the clip rect applies
        pygame.draw.rect(state.screen, color_rgb(color_index),
                         viewport_clip)

def pset(x, y, color_index):
    sx, sy = int(x - state.cam_x), int(y - state.cam_y)
    if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
        state.screen.set_at((sx, sy), color_rgb(color_index))

def pget(x, y):
    """Returns the palette index of the color at (x,y)."""
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
    _blend_fill_rect(int(x), int(y), int(w), int(h), color_index)

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
    if r <= 0:
        return
    m = getattr(state, "blend_mode", "normal")
    if m == "normal":
        pygame.draw.circle(state.screen, color_rgb(color_index),
                           (int(x - state.cam_x), int(y - state.cam_y)),
                           int(r))
        return
    # Draw to scratch surface with colorkey for transparency, then blend-blit
    d = int(r) * 2 + 2
    tmp = _scratch_surface(d, d)
    tmp.fill((0, 0, 0))
    tmp.set_colorkey((0, 0, 0))
    pygame.draw.circle(tmp, color_rgb(color_index),
                       (d // 2, d // 2), int(r))
    if m == "alpha":
        tmp.set_alpha(state.blend_alpha)
        flag = 0
    else:
        tmp.set_alpha(255)
        flag = _blend_flag()
    state.screen.blit(tmp,
                      (int(x - state.cam_x) - d // 2,
                       int(y - state.cam_y) - d // 2),
                      special_flags=flag)

# ======================================================================
# TEXT (with font cache)
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
    """Zeichnet Text. Wenn upper=True: input wird automatisch
    .upper() applied (default for all UI elements).
    Wenn upper=False: Kleinbuchstaben werden auf das Grossbuchstaben-
    Glyph gemappt, da der 3x5-Font keine echten Kleinbuchstaben hat
    - but the string itself stays unchanged (important for
    Cursor-Positionierung im Code-Editor)."""
    s = str(string)
    if upper:
        s = s.upper()
    px, py = x, y
    m = getattr(state, "blend_mode", "normal")
    flag = _blend_flag() if m != "normal" else 0
    use_alpha = (m == "alpha")
    for char in s:
        if char == '\n':
            py += 6
            px = x
            continue
        glyph_char = char
        if not upper and 'a' <= char <= 'z':
            glyph_char = char.upper()
        key = (glyph_char, color_index & 0xFF)
        if key not in state.font_cache:
            state.font_cache[key] = _build_char_surface(glyph_char, color_index)
        glyph_surf = state.font_cache[key]
        if use_alpha:
            # For alpha mode we need to temporarily set alpha on a copy
            tmp = glyph_surf.copy()
            tmp.set_alpha(state.blend_alpha)
            state.screen.blit(tmp, (px - state.cam_x, py - state.cam_y))
        elif flag:
            state.screen.blit(glyph_surf,
                              (px - state.cam_x, py - state.cam_y),
                              special_flags=flag)
        else:
            state.screen.blit(glyph_surf,
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
