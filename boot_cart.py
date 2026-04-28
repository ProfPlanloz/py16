"""
boot_cart.py - Beispiel-Boot-Cart fuer py-16
=============================================

Ein hubescher Cart-Browser, der als Boot-Cart benutzt werden kann.
Listet alle Carts im Cart-Verzeichnis (ausser sich selbst), zeigt
einfache Cover-Vorschauen und startet ausgewaehlte Carts mit
push_cart() - so kommt man mit pop_cart() (intern: F12 -> BIOS) wieder
zurueck zum Browser.

# @manual
# @description
# Boot-Cart fuer py-16. Browse durch deine Cart-Sammlung mit
# Cover-Vorschauen.
#
# @controls
# Pfeile      : Navigation durch die Cart-Liste
# Enter/Space : Ausgewaehlten Cart starten
# F12         : Zurueck ins BIOS
# F6          : Code-Editor
# @end

Installation:
  Diese Datei mit py-16 oeffnen, im Code-Editor F5 druecken,
  als 'boot.p16' im Cart-Verzeichnis (~/.py16/carts/) speichern.
  Beim naechsten Start laedt py-16 sie automatisch.
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
# COVER-VORSCHAU
# ----------------------------------------------------------------------

def _draw_cover_box(x, y, w, h, path, name, is_pdf, selected):
    # Rahmen
    bg = 13 if selected else 1
    py16.rectfill(x, y, w, h, bg)
    py16.rect(x, y, w, h, 7 if selected else 5)

    # Cover-Bereich (oberes 2/3)
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

    # Fallback wenn kein Cover verfuegbar: stilisiertes Symbol
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

# Cover-Cache: zur Laufzeit, damit jedes Cart-Cover nur einmal pro Session
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
    # Verzeichnis alle 60 Frames neu pruefen (Hot-Plug-Support)
    if py16.t() - B.last_dir_check > 60 or not B.cart_list:
        _refresh_carts()
        B.last_dir_check = py16.t()

    n = len(B.cart_list)
    if n == 0:
        return

    # Pfeil-Navigation: 2 Spalten, also left/right ist horizontal,
    # up/down vertikal in der 2-spaltigen Liste
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
        py16.text("KEINE CARTS GEFUNDEN", 60, 80, 8)
        py16.text("LEGE .P16/.PDF IN", 60, 100, 6)
        try:
            from py16 import config
            py16.text(config.carts_dir()[:40], 60, 108, 7, upper=False)
        except Exception:
            pass
        py16.text("F12 ZURUECK INS BIOS", 60, 130, 6)
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
    py16.text(f"SEITE {cur_page}/{total_pages}",
              py16.WIDTH - 60, py16.HEIGHT - 26, 6)

    # Footer
    py16.rectfill(0, py16.HEIGHT - 16, py16.WIDTH, 16, 13)
    py16.text("PFEILE NAV  ENTER START", 4, py16.HEIGHT - 13, 6)
    py16.text("F12 BIOS  F6 EDITOR", 4, py16.HEIGHT - 5, 6)

def init():
    py16.set_code_file(__file__)
    _refresh_carts()

if __name__ == "__main__":
    py16.run(update, draw, init)
