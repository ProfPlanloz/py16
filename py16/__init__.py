"""
py-16 Fantasy Console
=====================
Eine 2D-Engine im Stil der 16-Bit-Aera.

  - 256 x 224 Pixel @ 60 FPS
  - 256-Farben-Palette (frei zuweisbar)
  - 1024 Sprites (8x8) im Sheet, optional als groessere Cels (bis 64x64)
  - Map mit 128 x 128 Tiles, Multi-Layer-Rendering ueber Sprite-Flags
  - 8 Sound-Kanaele mit 4 Wellenformen
  - Eingebauter Sprite-Editor (F1) und Map-Editor (F2)
  - Cart-Save/Load (F5/F8) im JSON-Format

Verwendung:

    import py16

    def init():
        py16.sset(8, 0, 8)         # ein roter Pixel
        py16.fset(1, 0, True)      # Flag 0 fuer Sprite 1

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
# Konstanten und Hauptschleife
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
# Sprites
# ----------------------------------------------------------------------
from .sprites import (
    sset, sget,
    spr,
    load_spritesheet,
)

# ----------------------------------------------------------------------
# Map und Flags
# ----------------------------------------------------------------------
from .maps import (
    mset, mget,
    draw_map,
    fset, fget,
)

# ----------------------------------------------------------------------
# Eingabe
# ----------------------------------------------------------------------
from .input import (
    btn, btnp,
    mouse_x, mouse_y,
    mouse_btn, mouse_btnp,
)

# ----------------------------------------------------------------------
# Audio
# ----------------------------------------------------------------------
from .audio import (
    tone,
    WAVE_SQUARE, WAVE_TRIANGLE, WAVE_SAW, WAVE_NOISE,
)
from .tracker import sfx, music

# ----------------------------------------------------------------------
# Mathe und Engine-Helfer
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
    """Zurueck zum BIOS-Bildschirm. Wird im naechsten Frame aktiv."""
    from . import bios
    bios.go_to_bios()

# PDF-Export-Funktion (optional - braucht reportlab+pypdf)
def export_pdf(filename, title=None, author=None):
    """Exportiert den aktuellen Cart als PDF mit Handbuch und eingebettetem Cart."""
    from . import cart_pdf
    return cart_pdf.export_pdf(filename, title=title, author=author)

# PDF-Cover-Extraktion fuer Boot-Carts (optional - braucht pymupdf)
def get_cart_cover(pdf_path, cell_w=64, cell_h=48):
    """Extrahiert das Cover einer PDF und liefert ein 2D-Array
    von Paletten-Indizes [row][col]. Liefert None wenn PDF kein Cover
    hat oder pymupdf nicht installiert ist."""
    from . import cart_covers
    return cart_covers.cover_to_palette_indices(pdf_path, cell_w, cell_h)

# ----------------------------------------------------------------------
# Code-Editor
# ----------------------------------------------------------------------
def set_code_file(path):
    """Verbindet den Code-Editor mit einer externen .py-Datei.
    Aufruf in init() z.B. mit __file__ - so kann der Editor die laufende
    Datei live bearbeiten.

    Akzeptiert None oder einen nicht existierenden Pfad; in dem Fall
    bleibt der Editor an seinem aktuellen Inhalt. Das ist wichtig wenn
    ein Cart aus einem .p16/.pdf geladen wird, wo __file__ nicht zur
    laufenden Datei passt."""
    import os
    from . import state, code_editor
    if not path:
        return
    if not os.path.exists(path):
        # Datei existiert nicht - cart_code_file trotzdem setzen, damit
        # ein spaeteres Save dort hin schreiben kann
        state.cart_code_file = path
        return
    state.cart_code_file = path
    code_editor._ensure_state()
    code_editor._load_external_if_present()

def set_cart_code(code_text):
    """Setzt den Cart-Code als String (programmatisch). Synct den
    Editor-Buffer mit. Praktisch fuer Tests oder zum Bauen von Carts
    direkt in Python ohne Editor-UI."""
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
    # Sprites
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
