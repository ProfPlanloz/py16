"""
py-16 Fantasy Console
=====================
A 2D engine in the style of the 16-bit era.

  - 256 x 224 Pixel @ 60 FPS
  - 256-Farben-Palette (frei zuweisbar)
  - 1024 sprites (8x8) in the sheet, optionally larger cels (up to 64x64)
  - Map with 128x128 tiles, multi-layer rendering via sprite flags
  - 8 sound channels with 4 waveforms
  - Built-in sprite editor (F1) and map editor (F2)
  - Cart-Save/Load (F5/F8) im JSON-Format

Usage:

    import py16

    def init():
        py16.sset(8, 0, 8)         # ein roter Pixel
        py16.fset(1, 0, True)      # Flag 0 for sprite 1

    def update():
        if py16.btn('right'):
            ...

    def draw():
        py16.cls(0)
        py16.spr(1, 100, 50)
        py16.text("HELLO", 4, 4, 7)

    py16.run(update, draw, init)
"""

# ----------------------------------------------------------------------
# constants and main loop
# ----------------------------------------------------------------------
from .core import (
    WIDTH, HEIGHT, SCALE, FPS,
    SHEET_SIZE, SPRITES_PER_ROW, SPRITE_PIX,
    MAP_W, MAP_H,
    PALETTE,
    run,
    toggle_fullscreen,
)

# ----------------------------------------------------------------------
# Grafik
# ----------------------------------------------------------------------
from .graphics import (
    camera, clip,
    cls, pset, pget,
    rect, rectfill, line, circ, circfill,
    text,
    pal, palt,
)

# ----------------------------------------------------------------------
# sprites
# ----------------------------------------------------------------------
from .sprites import (
    sset, sget,
    spr,
    load_spritesheet,
)

# ----------------------------------------------------------------------
# Map and Flags
# ----------------------------------------------------------------------
from .maps import (
    mset, mget, mclear,
    draw_map,
    fset, fget,
    NUM_LAYERS,
)
from .mode7 import (
    mode7,
    mode7_wave, mode7_earthquake, mode7_tunnel, mode7_curve,
)

# ----------------------------------------------------------------------
# input
# ----------------------------------------------------------------------
from .input import (
    btn, btnp,
    mouse_x, mouse_y,
    mouse_btn, mouse_btnp,
)
# Multi-player support
from .controller import (
    player_connected, player_count, player_name,
    num_connected as num_controllers,
    MAX_PLAYERS,
)

# ----------------------------------------------------------------------
# Audio
# ----------------------------------------------------------------------
from .audio import (
    tone,
    WAVE_SQUARE, WAVE_TRIANGLE, WAVE_SAW, WAVE_NOISE,
)
from .tracker import sfx, music
from .samples import (
    load_sample, play_sample, clear_sample,
    set_sample_name, set_sample_base_note,
    NUM_SAMPLES,
)

# ----------------------------------------------------------------------
# Mathe and Engine-Helfer
# ----------------------------------------------------------------------
from .mathx import (
    rnd, flr, ceil, abs_, mid,
    sin, cos, atan2, sqrt,
    t, fps,
)

# ----------------------------------------------------------------------
# Cart
# ----------------------------------------------------------------------
from .cart import save_cart, load_cart
from .cart_runtime import (
    run_cart, push_cart, pop_cart,
    cart_stack_depth, current_cart_file,
)

def go_to_bios():
    """Back to BIOS screen. Becomes active next frame."""
    from . import bios
    bios.go_to_bios()

# PDF export function (optional - needs reportlab+pypdf)
def export_pdf(filename, title=None, author=None):
    """Exports the current cart as a PDF with manual and embedded cart."""
    from . import cart_pdf
    return cart_pdf.export_pdf(filename, title=title, author=author)

# PDF cover extraction for boot carts (optional - needs pymupdf)
def get_cart_cover(pdf_path, cell_w=64, cell_h=48):
    """Extracts the cover of a PDF and returns a 2D array
    von Paletten-Indizes [row][col]. Returns None if PDF kein Cover
    hat or pymupdf not installiert ."""
    from . import cart_covers
    return cart_covers.cover_to_palette_indices(pdf_path, cell_w, cell_h)

# ----------------------------------------------------------------------
# Code-Editor
# ----------------------------------------------------------------------
def set_code_file(path):
    """Connects den Code-Editor with einer externen .py-file.
    call in init() z.B. with __file__ - so can der Editor die laufende
    file live bearbeiten.

    Akzeptiert None or einen not existierenden Pfad; in dem Fall
    the editor keeps its current content. This matters when
    a cart is loaded from .p16/.pdf, where __file__ doesn't match
    laufenden file passt."""
    import os
    from . import state, code_editor
    if not path:
        return
    if not os.path.exists(path):
        # file existiert not - cart_code_file despitedem setzen, damit
        # ein lateres Save dort hin schreiben can
        state.cart_code_file = path
        return
    state.cart_code_file = path
    code_editor._ensure_state()
    code_editor._load_external_if_present()

def set_cart_code(code_text):
    """Sets den Cart-Code als String (programmatisch). Synct den
    editor buffer too. Useful for tests or building carts
    directly in Python without editor UI."""
    from . import state, code_editor
    state.cart_code = code_text
    code_editor._ensure_state()
    state.ce_lines = code_editor._text_to_lines(code_text)
    state.ce_cur_row = 0
    state.ce_cur_col = 0
    state.ce_dirty = False

__version__ = "1.0.0"
__all__ = [
    # Core
    "WIDTH", "HEIGHT", "SCALE", "FPS",
    "SHEET_SIZE", "SPRITES_PER_ROW", "SPRITE_PIX",
    "MAP_W", "MAP_H", "PALETTE", "run", "toggle_fullscreen",
    # Graphics
    "camera", "clip",
    "cls", "pset", "pget",
    "rect", "rectfill", "line", "circ", "circfill",
    "text", "pal", "palt",
    # sprites
    "sset", "sget", "spr", "load_spritesheet",
    # Maps
    "mset", "mget", "draw_map", "fset", "fget",
    # Input
    "btn", "btnp",
    "mouse_x", "mouse_y", "mouse_btn", "mouse_btnp",
    # Audio
    "sfx", "music", "tone",
    "WAVE_SQUARE", "WAVE_TRIANGLE", "WAVE_SAW", "WAVE_NOISE",
    # Math
    "rnd", "flr", "ceil", "abs_", "mid",
    "sin", "cos", "atan2", "sqrt",
    "t", "fps",
    # Cart
    "save_cart", "load_cart", "export_pdf", "get_cart_cover",
    "set_code_file", "set_cart_code",
    "run_cart", "push_cart", "pop_cart",
    "cart_stack_depth", "current_cart_file", "go_to_bios",
]
