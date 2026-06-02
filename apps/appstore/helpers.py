"""Reine Hilfsfunktionen ohne eigenen Zustand (bis auf Lesen aus S).

Routing, Katalog-Abfragen, Textumbruch, .p16img-Parsing/Blitting und das
Layout. Diese Funktionen haben keine Seiteneffekte ausser Zeichnen
(blit_icon) bzw. Lesen von S (visible_items).
"""
import os
import py16

from .config import ROUTING_RULES, FALLBACK_DEST, FILTERS, ROW_H, TYPE_ICONS, TYPE_ICON_DIRS
from .state import S


# === Routing ===

def dest_for(rel_path):
    """Pfad im Repo -> lokales Ziel anhand ROUTING_RULES."""
    rel_low = rel_path.lower().lstrip("/")
    base = os.path.basename(rel_path)
    for rule in ROUTING_RULES:
        if rel_low.startswith(rule["prefix"].lower()) and rel_low.endswith(rule["ext"].lower()):
            return os.path.join(rule["dest"], base) if rule["dest"] != "." else base
    return base if FALLBACK_DEST == "." else os.path.join(FALLBACK_DEST, base)


# === Katalog-Abfragen ===

def item_kind(item):
    """Typ eines Eintrags aus den Datei-Endungen ableiten."""
    exts = [os.path.splitext(f)[1].lower() for f in item.get("files", [])]
    if ".py" in exts:
        return "app"
    if ".pdf" in exts or ".p16" in exts:
        return "cart"
    if ".p16img" in exts:
        return "icon"
    if ".p16canvas" in exts:
        return "canvas"   # Wallpaper
    if ".p16mov" in exts:
        return "movie"    # Animation
    if ".p16sheet" in exts:
        return "sheet"    # Spritesheet-Animation
    return "other"


def visible_items():
    """Liste gefiltert nach aktivem Tab."""
    if S.filter is None:
        return S.items
    return [it for it in S.items if item_kind(it) == S.filter]


def item_icon_ref(item):
    """Repo-relativer Pfad des ersten .p16img eines Eintrags, sonst None."""
    for f in item.get("files", []):
        if str(f).lower().endswith(".p16img"):
            return str(f).lstrip("/")
    return None


def type_icon_path(kind):
    """Lokalen Pfad zum Typ-Icon fuer ein item_kind finden, sonst None.

    Sucht in TYPE_ICON_DIRS; der erste existierende Treffer gewinnt. Dient
    als Fallback fuer Eintraege ohne eigenes .p16img (Carts, Wallpaper,
    Animationen, Spritesheets).
    """
    name = TYPE_ICONS.get(kind)
    if not name:
        return None
    for d in TYPE_ICON_DIRS:
        p = name if d in ("", ".") else os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


def is_installed(item):
    """Heuristik: gilt als installiert, wenn alle Zieldateien lokal existieren."""
    files = item.get("files", [])
    if not files:
        return False
    return all(os.path.isfile(dest_for(f)) for f in files)


def item_downloads(item):
    """Echte Asset-Download-Zahl (max ueber zugehoerige Assets) oder None.

    Greift auf die aus den GitHub-Releases geladenen Zahlen (S.dl_counts) zu.
    None bedeutet: kein passendes Asset bekannt -> Aufrufer faellt auf das
    statische downloads-Feld zurueck.
    """
    best = None
    for f in item.get("files", []):
        c = S.dl_counts.get(os.path.basename(str(f)))
        if c is not None:
            best = c if best is None else max(best, c)
    return best


# === Text ===

def fmt_count(n):
    """Zahl kompakt darstellen: 999 -> '999', 1234 -> '1.2K', 2_000_000 -> '2.0M'."""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if n < 0:
        return "0"
    if n < 1000:
        return str(n)
    if n < 999500:
        return ("%.1fK" % (n / 1000.0)).replace(".0K", "K")
    return ("%.1fM" % (n / 1000000.0)).replace(".0M", "M")


def wrap(s, width):
    """Wortweiser Umbruch auf width Zeichen; lange Tokens werden hart gebrochen."""
    width = max(1, width)
    out = []
    cur = ""
    for word in str(s).split():
        while len(word) > width:
            if cur:
                out.append(cur)
                cur = ""
            out.append(word[:width])
            word = word[width:]
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= width:
            cur += " " + word
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


# === .p16img ===

def hexval(c):
    """Ein Zeichen -> Palettenindex 0..15. Ungueltiges -> 7 (transparent)."""
    try:
        v = int(c, 16)
        return v if 0 <= v <= 15 else 7
    except Exception:
        return 7


def parse_p16img(text):
    """Text einer .p16img-Datei -> (w, h, grid[y][x]=index) oder None."""
    w = h = 0
    rows = []
    for raw in text.split("\n"):
        s = raw.rstrip("\r")
        if not s:
            continue
        if s.lstrip().startswith("#"):
            for tok in s.lower().replace("x", " ").split():
                if tok.isdigit():
                    if w == 0:
                        w = int(tok)
                    elif h == 0:
                        h = int(tok)
            continue
        rows.append(s)
    if not rows:
        return None
    if w == 0:
        w = max(len(r) for r in rows)
    if h == 0:
        h = len(rows)
    grid = []
    for y in range(h):
        r = rows[y] if y < len(rows) else ""
        grid.append([hexval(r[x]) if x < len(r) else 7 for x in range(w)])
    return (w, h, grid)


def blit_icon(ox, oy, scale, img):
    """Icon-Grid an (ox,oy) mit ganzzahligem Zoom zeichnen (7 = transparent).

    Run-Length pro Zeile spart viele rectfill-Aufrufe.
    """
    iw, ih, grid = img
    for y in range(ih):
        row = grid[y]
        x = 0
        while x < iw:
            c = row[x]
            x2 = x
            while x2 < iw and row[x2] == c:
                x2 += 1
            if c != 7:
                py16.rectfill(ox + x * scale, oy + y * scale, (x2 - x) * scale, scale, c)
            x = x2


# === Layout ===

def layout(ww, wh):
    """Alle Layout-Offsets relativ zur Fenster-Ecke (wx, wy)."""
    btn_y = wh - 24
    list_y = 32
    list_h = max(12, btn_y - 4 - list_y)
    sb_x = ww - 12
    # Drei gleich breite Buttons fuer die Listenansicht (REFRESH | INFO | INSTALL)
    bw = max(28, (ww - 16) // 3)
    return {
        "sel_y": 14,
        "sel_h": 9,
        "arrow_w": 22,
        "status_y": 24,
        "list_y": list_y,
        "list_h": list_h,
        "list_w": sb_x - 6,
        "sb_x": sb_x,
        "btn_y": btn_y,
        "foot_y": wh - 12,
        "visible_rows": max(1, list_h // ROW_H),
        "btn_w": bw,
        "btn1_x": 6,
        "btn2_x": 6 + bw + 2,
        "btn3_x": ww - 6 - bw,
    }
