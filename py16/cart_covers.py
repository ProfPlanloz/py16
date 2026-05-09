"""
py16.cart_covers
================
Extracts the cover (first page) from a PDF cart and returns it
as a small bitmap for the boot-cart browser.

Cache: rendered covers land in ~/.py16/cart_covers/ as PNG,
keyed by mtime of the cart file. On re-render, cache is
compared so it doesn't re-render every start.

Format: 96x128 pixel PNG previews, sized for the 2x3 grid of the
the boot cart.
"""

import os
import io
import hashlib

try:
    import pymupdf
    _HAS_PYMUPDF = True
except ImportError:
    try:
        import fitz as pymupdf  # old name for pymupdf
        _HAS_PYMUPDF = True
    except ImportError:
        _HAS_PYMUPDF = False

# Cover-preview-Aufloesung
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
    """Path to the cached PNG preview for a PDF."""
    # Hash of the absolute path so different PDFs with the same
    # filename don't collide
    h = hashlib.md5(os.path.abspath(pdf_path).encode("utf-8")).hexdigest()[:12]
    base = os.path.basename(pdf_path).rsplit(".", 1)[0]
    return os.path.join(_cache_dir(), f"{base}_{h}.png")

def _is_cache_valid(pdf_path, cache_path):
    """Cache is valid if the cache file is newer than the PDF."""
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
    """Extracts the first page of a PDF as a PIL image in preview format.
    Returns None if pymupdf is not installed or the cart is not a PDF
    ."""
    if not _HAS_PYMUPDF:
        return None
    if not os.path.exists(pdf_path):
        return None

    cache_path = _cache_path(pdf_path)

    # Load from cache if possible
    if _is_cache_valid(pdf_path, cache_path):
        try:
            from PIL import Image
            return Image.open(cache_path)
        except Exception:
            pass

    # PDF open and erste page rendern
    try:
        doc = pymupdf.open(pdf_path)
        if doc.page_count < 1:
            doc.close()
            return None
        page = doc[0]
        # Render at larger resolution, then post-process
        zoom = 200 / page.rect.width   # results in ~200 pixels wide
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")
        doc.close()

        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        # Write to cache (preserve original aspect)
        try:
            img.save(cache_path, "PNG")
        except Exception:
            pass
        return img
    except Exception as e:
        print(f"Cover extraction failed ({pdf_path}): {e}")
        return None

# ----------------------------------------------------------------------
# COVER AS PALETTE INDICES (for sprite-sheet rendering)
# ----------------------------------------------------------------------

def cover_to_palette_indices(pdf_path, cell_w, cell_h):
    """
    Returns a 2D array of palette indices (nearest neighbor in the
    256-color palette), size cell_w x cell_h, that can be directly
    rendered with pset/sset. Ideal for the boot-cart browser.
    Returns None on error.
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
        idx = d.argmin(-1)                            # (H, W)
        return idx.tolist()
    except ImportError:
        # Fallback without numpy: pixel-by-pixel
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
    """Returns True if pymupdf is installed."""
    return _HAS_PYMUPDF

# ----------------------------------------------------------------------
# CACHE CLEANUP
# ----------------------------------------------------------------------

def _all_known_cart_hashes():
    """Returns a set of MD5 hashes (12-char prefix) of all PDF carts
    currently in the configured carts dir. Used to detect cache files
    whose source cart has been deleted."""
    from . import config
    known = set()
    try:
        for path in config.list_carts():
            if path.lower().endswith(".pdf"):
                h = hashlib.md5(
                    os.path.abspath(path).encode("utf-8")
                ).hexdigest()[:12]
                known.add(h)
    except Exception:
        pass
    return known

def _parse_cache_filename(filename):
    """Cache files are named '<base>_<12char-hex>.png'.
    Returns (base, hash) or None if filename doesn't match."""
    if not filename.endswith(".png"):
        return None
    name = filename[:-4]
    if len(name) < 14:
        return None
    if name[-13] != "_":
        return None
    h = name[-12:]
    if not all(c in "0123456789abcdef" for c in h):
        return None
    base = name[:-13]
    return (base, h)

def cleanup_cache(max_age_days=None, max_size_mb=None,
                  remove_orphans=True, dry_run=False):
    """Cleans up the cover cache directory.

    Three independent cleanup rules can be combined:

    - remove_orphans : remove cache entries whose source cart no longer
                       exists in the carts dir (default: True)
    - max_age_days   : remove cache entries older than N days
                       (None = no age limit)
    - max_size_mb    : keep total cache size under N MB by removing
                       oldest entries first (None = no size limit)

    dry_run : if True, only report what would be removed without
              actually deleting files.

    Returns a dict with stats:
        {"removed": int, "kept": int, "freed_bytes": int,
         "removed_files": [list of paths]}
    """
    import time

    cache = _cache_dir()
    if not os.path.isdir(cache):
        return {"removed": 0, "kept": 0, "freed_bytes": 0, "removed_files": []}

    known_hashes = _all_known_cart_hashes() if remove_orphans else None
    now = time.time()
    age_cutoff = (now - max_age_days * 86400) if max_age_days else None

    # First pass: catalog all cache files
    entries = []
    for fname in os.listdir(cache):
        full = os.path.join(cache, fname)
        if not os.path.isfile(full):
            continue
        parsed = _parse_cache_filename(fname)
        if parsed is None:
            continue   # not a cache file, skip
        _base, h = parsed
        try:
            stat = os.stat(full)
            entries.append({
                "path":  full,
                "name":  fname,
                "hash":  h,
                "size":  stat.st_size,
                "mtime": stat.st_mtime,
            })
        except OSError:
            continue

    # Decide which entries to remove based on the three rules
    to_remove = []
    keep = []
    for e in entries:
        reason = None
        if remove_orphans and known_hashes is not None and e["hash"] not in known_hashes:
            reason = "orphan"
        elif age_cutoff is not None and e["mtime"] < age_cutoff:
            reason = "age"
        if reason:
            to_remove.append((e, reason))
        else:
            keep.append(e)

    # Apply size limit by removing oldest "keep" entries until under limit
    if max_size_mb is not None:
        max_bytes = max_size_mb * 1024 * 1024
        keep.sort(key=lambda e: e["mtime"], reverse=True)  # newest first
        running = 0
        new_keep = []
        for e in keep:
            if running + e["size"] <= max_bytes:
                new_keep.append(e)
                running += e["size"]
            else:
                to_remove.append((e, "size"))
        keep = new_keep

    # Execute the removal
    freed = 0
    removed_files = []
    for e, _reason in to_remove:
        if not dry_run:
            try:
                os.remove(e["path"])
            except OSError:
                continue
        freed += e["size"]
        removed_files.append(e["path"])

    return {
        "removed":       len(removed_files),
        "kept":          len(keep),
        "freed_bytes":   freed,
        "removed_files": removed_files,
    }

def cache_stats():
    """Returns current cache stats: file count, total size, oldest/newest entry."""
    cache = _cache_dir()
    if not os.path.isdir(cache):
        return {"count": 0, "total_bytes": 0, "oldest": None, "newest": None}

    count = 0
    total = 0
    oldest = None
    newest = None
    for fname in os.listdir(cache):
        full = os.path.join(cache, fname)
        if not os.path.isfile(full) or not _parse_cache_filename(fname):
            continue
        try:
            stat = os.stat(full)
        except OSError:
            continue
        count += 1
        total += stat.st_size
        if oldest is None or stat.st_mtime < oldest:
            oldest = stat.st_mtime
        if newest is None or stat.st_mtime > newest:
            newest = stat.st_mtime
    return {
        "count":       count,
        "total_bytes": total,
        "oldest":      oldest,
        "newest":      newest,
    }
