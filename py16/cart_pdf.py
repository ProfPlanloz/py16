"""
py16.cart_pdf
=============
Cart als PDF-Handbuch exportieren und aus PDF wieder laden.

Ein PDF-Cart enthaelt:
  - Seite 1: Cover (Cart-Name, Sprite-Sheet als Hintergrund, Datum)
  - Seite 2: Beschreibung (aus @manual/@end-Kommentar im Code)
  - Seite 3: Asset-Uebersicht (Sprite-Sheet, Map-Mini, SFX-Liste, Tracks)
  - Seite 4+: Code-Listing im 80er-Stil (mit Zeilennummern)
  - Anhang: Das eigentliche .p16-Cart als Datei-Attachment

Lesen via pypdf, Schreiben via reportlab (beide optional).
"""

import os
import io
import json
import base64
import datetime

from . import state
from .core import PALETTE, SHEET_SIZE, MAP_W, MAP_H

# ----------------------------------------------------------------------
# OPTIONALE ABHAENGIGKEITEN
# ----------------------------------------------------------------------

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as _rl_colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as _rl_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

try:
    from pypdf import PdfReader, PdfWriter
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ----------------------------------------------------------------------
# HELFER
# ----------------------------------------------------------------------

def _check_dependencies():
    missing = []
    if not _HAS_REPORTLAB:
        missing.append("reportlab")
    if not _HAS_PYPDF:
        missing.append("pypdf")
    return missing

def _extract_manual(code_text):
    """Extrahiert den Inhalt zwischen # @manual und # @end aus dem Code.
    Liefert (description, controls, credits)."""
    if not code_text:
        return None
    lines = code_text.split("\n")
    in_manual = False
    section = "description"
    sections = {"description": [], "controls": [], "credits": []}
    for line in lines:
        s = line.strip()
        if s.startswith("# @manual"):
            in_manual = True
            continue
        if s.startswith("# @end"):
            in_manual = False
            continue
        if not in_manual:
            continue
        # Section-Marker erkennen
        if s.startswith("# @controls"):
            section = "controls"
            continue
        if s.startswith("# @credits"):
            section = "credits"
            continue
        if s.startswith("# @description"):
            section = "description"
            continue
        # Kommentarzeichen entfernen
        if s.startswith("#"):
            text = s[1:].strip()
            sections[section].append(text)
    if not any(sections.values()):
        return None
    return sections

def _make_sprite_sheet_image(crop_to_used=False):
    """Erzeugt ein PIL-Image vom aktuellen Sprite-Sheet.
    Wenn crop_to_used=True: schneidet auf den belegten Bereich zu."""
    try:
        from PIL import Image
    except ImportError:
        return None
    if state.sprite_sheet is None:
        return None
    import pygame
    if _HAS_NUMPY:
        arr = pygame.surfarray.array3d(state.sprite_sheet)
        # surfarray ist (W, H, 3), PIL erwartet (H, W, 3)
        arr = arr.transpose(1, 0, 2)
        img = Image.fromarray(arr.astype("uint8"))
    else:
        w, h = state.sprite_sheet.get_size()
        img = Image.new("RGB", (w, h))
        for y in range(h):
            for x in range(w):
                img.putpixel((x, y), tuple(state.sprite_sheet.get_at((x, y))[:3]))

    if crop_to_used:
        bbox = _used_bbox(img)
        if bbox is not None:
            # Auf naechsten 8-Pixel-Schritt aufrunden + ein bisschen Padding
            l, t, r, b = bbox
            l = (l // 8) * 8
            t = (t // 8) * 8
            r = ((r + 7) // 8) * 8
            b = ((b + 7) // 8) * 8
            # Mindestgroesse 32x32 fuer hueb"sche Anzeige
            if r - l < 32:
                r = min(SHEET_SIZE, l + 32)
            if b - t < 32:
                b = min(SHEET_SIZE, t + 32)
            img = img.crop((l, t, r, b))
    return img

def _used_bbox(img):
    """Liefert (left, top, right, bottom) der nicht-schwarzen Pixel."""
    w, h = img.size
    left, top, right, bottom = w, h, 0, 0
    found = False
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y][:3]
            if r > 0 or g > 0 or b > 0:
                if x < left: left = x
                if x > right: right = x
                if y < top: top = y
                if y > bottom: bottom = y
                found = True
    if not found:
        return None
    return left, top, right + 1, bottom + 1

def _make_map_image(scale=1):
    """Rendert die Map als kleines Bild (jeder Tile = scale Pixel)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    img = Image.new("RGB", (MAP_W * scale, MAP_H * scale), (16, 16, 32))
    if not state.map_data:
        return img
    # Fuer jede Map-Zelle: den dominanten Farbton des Sprites verwenden
    sprite_avg_colors = {}
    for y in range(MAP_H):
        for x in range(MAP_W):
            sid = state.map_data[y][x]
            if sid == 0:
                continue
            if sid not in sprite_avg_colors:
                sprite_avg_colors[sid] = _avg_sprite_color(sid)
            col = sprite_avg_colors[sid]
            for dy in range(scale):
                for dx in range(scale):
                    img.putpixel((x * scale + dx, y * scale + dy), col)
    return img

def _avg_sprite_color(sprite_id):
    """Liefert eine durchschnittliche Farbe eines Sprites."""
    import pygame
    if state.sprite_sheet is None:
        return (128, 128, 128)
    sx = (sprite_id % 32) * 8
    sy = (sprite_id // 32) * 8
    r_sum = g_sum = b_sum = count = 0
    for y in range(8):
        for x in range(8):
            r, g, b = state.sprite_sheet.get_at((sx + x, sy + y))[:3]
            if r == 0 and g == 0 and b == 0:
                continue   # transparent ueberspringen
            r_sum += r; g_sum += g; b_sum += b; count += 1
    if count == 0:
        return (32, 32, 32)
    return (r_sum // count, g_sum // count, b_sum // count)

# ----------------------------------------------------------------------
# PDF-EXPORT
# ----------------------------------------------------------------------

def export_pdf(filename, title=None, author=None):
    """Exportiert den aktuellen Cart als PDF-Handbuch mit eingebettetem Cart."""
    missing = _check_dependencies()
    if missing:
        print(f"PDF-Export braucht: {', '.join(missing)} (pip install {' '.join(missing)})")
        return False
    try:
        from PIL import Image  # fuer Pillow-Pruefung
    except ImportError:
        print("PDF-Export braucht: pillow (pip install pillow)")
        return False

    title = title or _derive_title(filename)
    author = author or "py-16 user"

    # 1) Erst das Cart als JSON in einen Buffer (das wird der Anhang)
    cart_buf = _build_cart_json()

    # 2) PDF mit reportlab schreiben
    pdf_buf = io.BytesIO()
    c = _rl_canvas.Canvas(pdf_buf, pagesize=A4)
    page_w, page_h = A4

    _draw_cover(c, page_w, page_h, title, author)
    c.showPage()

    manual = _extract_manual(getattr(state, "cart_code", ""))
    if manual:
        _draw_manual_page(c, page_w, page_h, title, manual)
        c.showPage()

    _draw_assets_page(c, page_w, page_h, title)
    c.showPage()

    code_text = getattr(state, "cart_code", "")
    if code_text:
        _draw_code_listing(c, page_w, page_h, title, code_text)

    c.save()

    # 3) Cart als Anhang einbetten via pypdf
    pdf_buf.seek(0)
    reader = PdfReader(pdf_buf)
    writer = PdfWriter(clone_from=reader)
    writer.add_attachment("cart.p16", cart_buf)

    with open(filename, "wb") as f:
        writer.write(f)
    print(f"PDF-Cart gespeichert: {filename}")
    return True

def _derive_title(filename):
    base = os.path.basename(filename)
    if base.lower().endswith(".pdf"):
        base = base[:-4]
    return base.upper().replace("_", " ").replace("-", " ") or "UNTITLED"

def _build_cart_json():
    """Erzeugt die Cart-JSON-Bytes (gleiches Format wie .p16)."""
    from .cart import save_cart
    tmp_path = "/tmp/_p16_pdf_attach.p16"
    save_cart(tmp_path)
    with open(tmp_path, "rb") as f:
        data = f.read()
    try:
        os.remove(tmp_path)
    except OSError:
        pass
    return data

# ----------------------------------------------------------------------
# COVER
# ----------------------------------------------------------------------

def _draw_cover(c, w, h, title, author):
    """Cover-Seite im Box-Stil."""
    # Hintergrund: Pico-Dunkelblau
    c.setFillColorRGB(29/255, 43/255, 83/255)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Titelband oben
    c.setFillColorRGB(255/255, 119/255, 168/255)
    c.rect(0, h - 80*mm, w, 30*mm, fill=1, stroke=0)

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(w / 2, h - 65*mm, title)

    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h - 75*mm, "PY-16 FANTASY CONSOLE CARTRIDGE")

    # Sprite-Sheet als grosses Cover-Bild in der Mitte
    img = _make_sprite_sheet_image(crop_to_used=True)
    if img is not None:
        # Schwarze (transparente) Pixel durch Cover-Hintergrundfarbe ersetzen,
        # damit Sprite-Transparenz nicht als schwarze Loecher auftaucht
        try:
            from PIL import Image
            bg_color = (29, 43, 83)  # Pico-Dunkelblau, gleicht Cover-Bg
            img_with_bg = Image.new("RGB", img.size, bg_color)
            pixels = img.load()
            target = img_with_bg.load()
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b = pixels[x, y][:3]
                    if r > 0 or g > 0 or b > 0:
                        target[x, y] = (r, g, b)
            img = img_with_bg
        except ImportError:
            pass

        cw, ch = img.size
        # Auf Pixel-Ebene upscalen mit nearest neighbor (4x)
        upscale = 4
        big = img.resize((cw * upscale, ch * upscale), 0)
        img_buf = io.BytesIO()
        big.save(img_buf, format="PNG")
        img_buf.seek(0)
        from reportlab.lib.utils import ImageReader

        # Maximale Display-Groesse: 130mm Breite ODER 130mm Hoehe
        MAX_MM = 130
        aspect = cw / ch
        if aspect >= 1:
            disp_w = MAX_MM
            disp_h = MAX_MM / aspect
        else:
            disp_h = MAX_MM
            disp_w = MAX_MM * aspect

        cx = (w - disp_w * mm) / 2
        cy = h - 100*mm - disp_h * mm
        c.drawImage(ImageReader(img_buf), cx, cy,
                    width=disp_w * mm, height=disp_h * mm)

    # Footer
    c.setFillColorRGB(255/255, 241/255, 232/255)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2, 30*mm, f"BY {author.upper()}")
    c.setFont("Helvetica", 9)
    today = datetime.date.today().isoformat()
    c.drawCentredString(w / 2, 22*mm, today)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(w / 2, 14*mm,
                        "OPEN THIS PDF WITH PY-16 TO PLAY")

# ----------------------------------------------------------------------
# MANUAL-SEITE (aus @manual-Kommentar)
# ----------------------------------------------------------------------

def _draw_manual_page(c, w, h, title, sections):
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Header
    c.setFillColorRGB(0.1, 0.15, 0.3)
    c.rect(0, h - 25*mm, w, 25*mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20*mm, h - 17*mm, title + " - HANDBUCH")

    y = h - 40*mm
    c.setFillColorRGB(0, 0, 0)

    if sections.get("description"):
        c.setFont("Helvetica-Bold", 13)
        c.drawString(20*mm, y, "BESCHREIBUNG")
        y -= 6*mm
        c.setFont("Helvetica", 11)
        for line in sections["description"]:
            if y < 30*mm:
                break
            c.drawString(20*mm, y, line)
            y -= 5*mm
        y -= 5*mm

    if sections.get("controls"):
        c.setFont("Helvetica-Bold", 13)
        c.drawString(20*mm, y, "STEUERUNG")
        y -= 6*mm
        c.setFont("Courier", 10)
        for line in sections["controls"]:
            if y < 30*mm:
                break
            c.drawString(20*mm, y, line)
            y -= 4.5*mm
        y -= 5*mm

    if sections.get("credits"):
        c.setFont("Helvetica-Bold", 13)
        c.drawString(20*mm, y, "CREDITS")
        y -= 6*mm
        c.setFont("Helvetica", 10)
        for line in sections["credits"]:
            if y < 30*mm:
                break
            c.drawString(20*mm, y, line)
            y -= 4.5*mm

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(w / 2, 12*mm, f"PY-16 CART - {title}")

# ----------------------------------------------------------------------
# ASSET-SEITE
# ----------------------------------------------------------------------

def _draw_assets_page(c, w, h, title):
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    c.setFillColorRGB(0.1, 0.15, 0.3)
    c.rect(0, h - 25*mm, w, 25*mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20*mm, h - 17*mm, title + " - ASSETS")

    c.setFillColorRGB(0, 0, 0)

    # Sprite-Sheet (links)
    sheet_img = _make_sprite_sheet_image()
    if sheet_img is not None:
        big = sheet_img.resize((400, 400), 0)
        buf = io.BytesIO()
        big.save(buf, format="PNG")
        buf.seek(0)
        from reportlab.lib.utils import ImageReader
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20*mm, h - 35*mm, "SPRITE SHEET (256x256)")
        c.drawImage(ImageReader(buf), 20*mm, h - 130*mm,
                    width=85*mm, height=85*mm)

    # Map (rechts oben)
    map_img = _make_map_image(scale=1)
    if map_img is not None:
        big = map_img.resize((256, 256), 0)
        buf = io.BytesIO()
        big.save(buf, format="PNG")
        buf.seek(0)
        from reportlab.lib.utils import ImageReader
        c.setFont("Helvetica-Bold", 11)
        c.drawString(115*mm, h - 35*mm, "MAP (128x128)")
        c.drawImage(ImageReader(buf), 115*mm, h - 130*mm,
                    width=75*mm, height=75*mm)

    # SFX-Liste
    y = h - 145*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, y, "SFX SLOTS")
    y -= 5*mm
    c.setFont("Courier", 8)
    sfx_patches = getattr(state, "sfx_patches", [])
    used_count = 0
    for i, p in enumerate(sfx_patches):
        if any(n[0] != 255 for n in p.get("notes", [])):
            used_count += 1
            note_count = sum(1 for n in p["notes"] if n[0] != 255)
            line = f"  SFX {i:02d}  speed={p['speed']:2}  notes={note_count:2}"
            col = i // 8
            row = used_count - 1 - col * 8
            if row < 8 and col < 4:
                c.drawString(20*mm + col * 45*mm,
                             y - row * 4*mm, line)

    # Music-Tracks
    y -= 40*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, y, "MUSIC TRACKS")
    y -= 5*mm
    c.setFont("Courier", 9)
    tracks = getattr(state, "music_tracks", [])
    for i, t in enumerate(tracks):
        if t and y > 25*mm:
            c.drawString(20*mm, y, f"  TRACK {i}  {len(t):2} patterns: {t[:8]}")
            y -= 4.5*mm

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(w / 2, 12*mm, f"PY-16 CART - {title}")

# ----------------------------------------------------------------------
# CODE-LISTING (80er-Stil)
# ----------------------------------------------------------------------

def _draw_code_listing(c, w, h, title, code_text):
    """Code als Listing mit Zeilennummern, evtl. mehrere Seiten."""
    lines = code_text.split("\n")
    page_idx = 0
    line_idx = 0
    LINES_PER_PAGE = 64
    LEFT = 20*mm
    TOP = h - 30*mm
    LINE_H = 3.4*mm

    while line_idx < len(lines):
        # Header
        c.setFillColorRGB(0.1, 0.15, 0.3)
        c.rect(0, h - 25*mm, w, 25*mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20*mm, h - 17*mm,
                     f"{title} - CODE LISTING (PAGE {page_idx + 1})")

        # Hellgrauer Hintergrund fuer Listing
        c.setFillColorRGB(0.97, 0.97, 0.95)
        c.rect(15*mm, 20*mm, w - 30*mm, h - 50*mm, fill=1, stroke=0)

        # Listing-Zeilen
        c.setFont("Courier", 8)
        for i in range(LINES_PER_PAGE):
            if line_idx >= len(lines):
                break
            y = TOP - i * LINE_H
            # Zeilennummer in Grau
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.drawString(LEFT, y, f"{line_idx + 1:4}")
            # Quelltext in Schwarz
            c.setFillColorRGB(0, 0, 0)
            line_text = lines[line_idx][:90]   # auf 90 Zeichen abschneiden
            c.drawString(LEFT + 10*mm, y, line_text)
            line_idx += 1

        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawCentredString(w / 2, 12*mm,
                            f"PY-16 CART - {title} - LINES "
                            f"{page_idx * LINES_PER_PAGE + 1} TO {line_idx}")

        if line_idx < len(lines):
            c.showPage()
        page_idx += 1

# ----------------------------------------------------------------------
# PDF LADEN (Cart-Anhang extrahieren)
# ----------------------------------------------------------------------

def load_pdf(filename):
    """Liest einen PDF-Cart und extrahiert das eingebettete .p16-Cart."""
    if not _HAS_PYPDF:
        print("PDF-Laden braucht: pypdf (pip install pypdf)")
        return False
    if not os.path.exists(filename):
        print(f"PDF '{filename}' nicht gefunden")
        return False

    reader = PdfReader(filename)
    attachments = reader.attachments
    if not attachments:
        print(f"PDF '{filename}' enthaelt keinen Cart-Anhang")
        return False

    cart_data = None
    for name, content_list in attachments.items():
        if name.lower().endswith(".p16") or name.lower() == "cart.p16":
            cart_data = content_list[0] if isinstance(content_list, list) else content_list
            break

    if cart_data is None:
        # Fallback: ersten Anhang nehmen
        first_name = next(iter(attachments))
        first_data = attachments[first_name]
        cart_data = first_data[0] if isinstance(first_data, list) else first_data

    # Temporaer schreiben und ueber save_cart-Loader einlesen
    tmp_path = "/tmp/_p16_pdf_load.p16"
    with open(tmp_path, "wb") as f:
        f.write(cart_data)
    from .cart import load_cart
    ok = load_cart(tmp_path)
    try:
        os.remove(tmp_path)
    except OSError:
        pass
    if ok:
        print(f"PDF-Cart geladen: {filename}")
    return ok
