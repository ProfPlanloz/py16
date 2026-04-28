"""
py16.cart_covers
================
Extrahiert das Cover (erste Seite) aus einem PDF-Cart und liefert es
als kleines Bitmap fuer den Boot-Cart-Browser.

Cache: gerenderte Cover landen unter ~/.py16/cart_covers/ als PNG,
indiziert nach mtime des Cart-Files. Beim Neu-Rendern wird gecached
verglichen, damit nicht bei jedem Start neu gerendert wird.

Format: 96x128 Pixel-PNG-Vorschauen, passend fuer das 2x3-Grid des
Boot-Carts.
"""

import os
import io
import hashlib

try:
    import pymupdf
    _HAS_PYMUPDF = True
except ImportError:
    try:
        import fitz as pymupdf  # alter Name fuer pymupdf
        _HAS_PYMUPDF = True
    except ImportError:
        _HAS_PYMUPDF = False

# Cover-Vorschau-Aufloesung
COVER_W = 96
COVER_H = 128

# ----------------------------------------------------------------------
# CACHE-VERWALTUNG
# ----------------------------------------------------------------------

def _cache_dir():
    from . import config
    cfg = config.get_config()
    d = os.path.expanduser(os.path.join(
        os.path.dirname(cfg["carts_dir"]) or "~/.py16", "cart_covers"))
    os.makedirs(d, exist_ok=True)
    return d

def _cache_path(pdf_path):
    """Pfad zur gecachten PNG-Vorschau fuer eine PDF."""
    # Hash des absoluten Pfads, damit verschiedene PDFs mit gleichem
    # Dateinamen kein Collision haben
    h = hashlib.md5(os.path.abspath(pdf_path).encode("utf-8")).hexdigest()[:12]
    base = os.path.basename(pdf_path).rsplit(".", 1)[0]
    return os.path.join(_cache_dir(), f"{base}_{h}.png")

def _is_cache_valid(pdf_path, cache_path):
    """Cache ist gueltig, wenn die Cache-Datei juenger ist als das PDF."""
    if not os.path.exists(cache_path):
        return False
    try:
        return os.path.getmtime(cache_path) >= os.path.getmtime(pdf_path)
    except OSError:
        return False

# ----------------------------------------------------------------------
# COVER-EXTRAKTION
# ----------------------------------------------------------------------

def extract_cover_png(pdf_path):
    """Extrahiert die erste Seite eines PDFs als PIL-Image im Vorschau-Format.
    Liefert None wenn pymupdf nicht installiert ist oder der Cart kein PDF
    ist."""
    if not _HAS_PYMUPDF:
        return None
    if not os.path.exists(pdf_path):
        return None

    cache_path = _cache_path(pdf_path)

    # Aus Cache laden wenn moeglich
    if _is_cache_valid(pdf_path, cache_path):
        try:
            from PIL import Image
            return Image.open(cache_path)
        except Exception:
            pass

    # PDF oeffnen und erste Seite rendern
    try:
        doc = pymupdf.open(pdf_path)
        if doc.page_count < 1:
            doc.close()
            return None
        page = doc[0]
        # Render auf grossere Aufloesung, dann nachbearbeiten
        zoom = 200 / page.rect.width   # ergibt ~200 Pixel breit
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")
        doc.close()

        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        # In Cache schreiben (Original-Aspekt erhalten)
        try:
            img.save(cache_path, "PNG")
        except Exception:
            pass
        return img
    except Exception as e:
        print(f"Cover-Extraktion fehlgeschlagen ({pdf_path}): {e}")
        return None

# ----------------------------------------------------------------------
# COVER ALS PALETTE-INDIZES (fuer Sprite-Sheet-Rendering)
# ----------------------------------------------------------------------

def cover_to_palette_indices(pdf_path, cell_w, cell_h):
    """
    Liefert ein 2D-Array von Paletten-Indizes (Naechster-Nachbar in der
    256-Farben-Palette), groesse cell_w x cell_h, der sich direkt mit
    pset/sset rendern laesst. Fuer den Boot-Cart-Browser ideal.
    Liefert None bei Fehler.
    """
    img = extract_cover_png(pdf_path)
    if img is None:
        return None
    try:
        from PIL import Image
        img = img.resize((cell_w, cell_h), Image.LANCZOS).convert("RGB")
    except Exception:
        return None

    from .core import PALETTE
    pal_arr = None
    try:
        import numpy as np
        arr = np.asarray(img, dtype=np.int32)            # (H, W, 3)
        pal_arr = np.array(PALETTE, dtype=np.int32)      # (256, 3)
        diff = arr[..., None, :] - pal_arr[None, None, :, :]
        dist = (diff * diff).sum(-1)
        idx = dist.argmin(-1)                            # (H, W)
        return idx.tolist()
    except ImportError:
        # Fallback ohne numpy: pixel-fuer-pixel
        pixels = img.load()
        result = [[0] * cell_w for _ in range(cell_h)]
        for y in range(cell_h):
            for x in range(cell_w):
                r, g, b = pixels[x, y]
                best, bd = 0, 1 << 30
                for i, (pr, pg, pb) in enumerate(PALETTE):
                    d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
                    if d < bd:
                        bd, best = d, i
                result[y][x] = best
        return result

def has_cover_support():
    """Liefert True wenn pymupdf installiert ist."""
    return _HAS_PYMUPDF
