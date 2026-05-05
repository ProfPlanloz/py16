"""
boot_cart.py - example boot cart for py-16
==========================================

A nicer cart browser that can be used as a boot cart. Lists all
carts in the cart directory (except itself), shows simple cover
previews, and starts selected carts with push_cart() - so you can
return to the browser with pop_cart() (or F12 -> BIOS).

# @manual
# @description
# Boot cart for py-16. Browse your cart collection with
# cover previews.
#
# @controls
# Arrows      : Navigate the cart list
# Enter/Space : Start selected cart
# F12         : Back to BIOS
# F6          : Code editor
# @end

Installation:
  Open this file with py-16, press F5 in the code editor,
  save as 'boot.p16' in the cart directory (~/.py16/carts/).
  Next launch py-16 will load it automatically.
"""

import os
import py16

# ----------------------------------------------------------------------
# STATE
# ----------------------------------------------------------------------

class _Browser:
    cart_list = []        # [(path, name, is_pdf), ...]
    cursor    = 0
    scroll    = 0
    last_dir_check = 0
    page_size = 6

B = _Browser()

# Visible-Layout: Carts werden in einem Grid mit Cover und Name angezeigt
COLS = 2
ROWS = 3            # 6 Carts pro "Seite"
CARD_W = 116
CARD_H = 60
GRID_X = 8
GRID_Y = 24

# ----------------------------------------------------------------------
# CART-LIST AKTUALISIEREN
# ----------------------------------------------------------------------

def _refresh_carts():
    """Cart-Liste vom Filesystem holen, Boot-Cart selbst ausschliessen."""
    try:
        from py16 import config
        all_carts = config.list_carts()
    except Exception:
        all_carts = []

    self_path = py16.current_cart_file()
    items = []
    for path in all_carts:
        if self_path and os.path.abspath(path) == os.path.abspath(self_path):
            continue
        name = os.path.basename(path)
        is_pdf = name.lower().endswith(".pdf")
        items.append((path, name, is_pdf))
    B.cart_list = items
    if B.cursor >= len(items):
        B.cursor = max(0, len(items) - 1)

# ----------------------------------------------------------------------
# COVER PREVIEW
# ----------------------------------------------------------------------

def _draw_cover_box(x, y, w, h, path, name, is_pdf, selected):
    # Rahmen
    bg = 13 if selected else 1
    py16.rectfill(x, y, w, h, bg)
    py16.rect(x, y, w, h, 7 if selected else 5)

    # Cover area (oberes 2/3)
    cover_h = h - 14
    cover_w = w - 4
    py16.rectfill(x + 2, y + 2, cover_w, cover_h, 0)

    # PDF: echtes Cover aus dem PDF extrahieren (gecached)
    cover_drawn = False
    if is_pdf:
        # Cover als Paletten-Indizes holen
        cover = _get_cached_cover(path, cover_w, cover_h)
        if cover is not None:
            for cy in range(cover_h):
                for cx in range(cover_w):
                    py16.pset(x + 2 + cx, y + 2 + cy, cover[cy][cx])
            cover_drawn = True

    # Fallback when no cover available: stylized symbol
    if not cover_drawn:
        if is_pdf:
            cx, cy = x + w // 2, y + cover_h // 2 + 2
            py16.rectfill(cx - 12, cy - 14, 24, 28, 7)
            py16.rectfill(cx - 11, cy - 13, 22, 26, 8)
            py16.rectfill(cx - 8, cy - 10, 16, 2, 7)
            py16.rectfill(cx - 8, cy - 6, 16, 1, 7)
            py16.rectfill(cx - 8, cy - 3, 12, 1, 7)
            py16.rectfill(cx - 8, cy, 14, 1, 7)
            py16.text("PDF", cx - 5, cy + 5, 11)
        else:
            cx, cy = x + w // 2, y + cover_h // 2 + 2
            py16.rectfill(cx - 14, cy - 8, 28, 16, 6)
            py16.rectfill(cx - 12, cy - 6, 24, 12, 13)
            py16.rectfill(cx - 14, cy + 4, 28, 4, 5)
            py16.text("P16", cx - 5, cy - 2, 12)

    # Name unten
    short = name
    if len(short) > 18:
        short = short[:15] + "..."
    nx = x + (w - len(short) * 4) // 2
    py16.text(short, nx, y + h - 9, 7, upper=False)

# Cover-Cache: at runtime, damit jedes Cart-Cover nur einmal pro Session
# aus dem PNG-Cache geholt wird
_cover_cache = {}

def _get_cached_cover(path, w, h):
    """Holt Cover als Paletten-Indizes mit Cache."""
    key = (path, w, h)
    if key not in _cover_cache:
        try:
            _cover_cache[key] = py16.get_cart_cover(path, w, h)
        except Exception:
            _cover_cache[key] = None
    return _cover_cache[key]

# ----------------------------------------------------------------------
# UPDATE / DRAW
# ----------------------------------------------------------------------

def update():
    # directory alle 60 Frames neu check (Hot-Plug-Support)
    if py16.t() - B.last_dir_check > 60 or not B.cart_list:
        _refresh_carts()
        B.last_dir_check = py16.t()

    n = len(B.cart_list)
    if n == 0:
        return

    # Arrow navigation: 2 columns, so left/right is horizontal,
    # up/down vertical in the 2-column list
    if py16.btnp('left'):
        if B.cursor % COLS > 0:
            B.cursor -= 1
    if py16.btnp('right'):
        if B.cursor % COLS < COLS - 1 and B.cursor + 1 < n:
            B.cursor += 1
    if py16.btnp('up'):
        if B.cursor >= COLS:
            B.cursor -= COLS
    if py16.btnp('down'):
        if B.cursor + COLS < n:
            B.cursor += COLS

    # Scroll
    page_idx = B.cursor // (COLS * ROWS)
    B.scroll = page_idx * (COLS * ROWS)

    # Enter/Space: Cart starten (push, damit Rueckkehr moeglich)
    if py16.btnp('enter') or py16.btnp('space'):
        if 0 <= B.cursor < n:
            path, _, _ = B.cart_list[B.cursor]
            py16.push_cart(path)

def draw():
    py16.cls(1)

    # Top-Bar
    py16.rectfill(0, 0, py16.WIDTH, 16, 13)
    py16.text("CART BROWSER", 4, 2, 7)
    py16.text(f"{len(B.cart_list):03d} CARTS", py16.WIDTH - 56, 2, 11)

    n = len(B.cart_list)
    if n == 0:
        py16.text("NO CARTS FOUND", 60, 80, 8)
        py16.text("PUT .P16/.PDF INTO", 60, 100, 6)
        try:
            from py16 import config
            py16.text(config.carts_dir()[:40], 60, 108, 7, upper=False)
        except Exception:
            pass
        py16.text("F12 BACK TO BIOS", 60, 130, 6)
        return

    # Grid mit Cart-Covers
    page_carts = B.cart_list[B.scroll:B.scroll + COLS * ROWS]
    for i, (path, name, is_pdf) in enumerate(page_carts):
        col = i % COLS
        row = i // COLS
        x = GRID_X + col * (CARD_W + 4)
        y = GRID_Y + row * (CARD_H + 4)
        absolute_idx = B.scroll + i
        selected = (absolute_idx == B.cursor)
        _draw_cover_box(x, y, CARD_W, CARD_H, path, name, is_pdf, selected)

    # Page-Indikator
    total_pages = (n + COLS * ROWS - 1) // (COLS * ROWS)
    cur_page = B.scroll // (COLS * ROWS) + 1
    py16.text(f"PAGE {cur_page}/{total_pages}",
              py16.WIDTH - 60, py16.HEIGHT - 26, 6)

    # Footer
    py16.rectfill(0, py16.HEIGHT - 16, py16.WIDTH, 16, 13)
    py16.text("ARROWS NAV  ENTER START", 4, py16.HEIGHT - 13, 6)
    py16.text("F12 BIOS  F6 EDITOR", 4, py16.HEIGHT - 5, 6)

def init():
    try:
        py16.set_code_file(__file__)
    except (NameError, Exception):
        pass
    _refresh_carts()

if __name__ == "__main__":
    py16.run(update, draw, init)
