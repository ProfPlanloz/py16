"""
py16.cart_pdf
=============
Export cart as PDF manual and load back from PDF.

A PDF cart contains:
  - Page 1: cover (cart name, sprite sheet as background, date)
  - Page 2: description (from @manual/@end comment in code)
  - Page 3: asset overview (sprite sheet, map mini, SFX list, tracks)
  - Page 4+: code listing in 80s style (with line numbers)
  - Attachment: The actual .p16 cart as file attachment

Read via pypdf, write via reportlab (both optional).
"""

import os
import io
import json
import base64
import datetime

from . import state
from .core import PALETTE, SHEET_SIZE, MAP_W, MAP_H

# ----------------------------------------------------------------------
# OPTIONAL DEPENDENCIES
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
    """Extracts the content between # @manual and # @end from code.
    Returns (description, controls, credits)."""
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
        # Detect section markers
        if s.startswith("# @controls"):
            section = "controls"
            continue
        if s.startswith("# @credits"):
            section = "credits"
            continue
        if s.startswith("# @description"):
            section = "description"
            continue
        # Strip comment markers
        if s.startswith("#"):
            text = s[1:].strip()
            sections[section].append(text)
    if not any(sections.values()):
        return None
    return sections

def _make_sprite_sheet_image(crop_to_used=False):
    """Creates ein PIL-Image vom currentn sprite sheet.
    If crop_to_used=True: crops to the used area."""
    try:
        from PIL import Image
    except ImportError:
        return None
    if state.sprite_sheet is None:
        return None
    import pygame
    if _HAS_NUMPY:
        arr = pygame.surfarray.array3d(state.sprite_sheet)
        # surfarray is (W, H, 3), PIL expects (H, W, 3)
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
            # Auf next 8-Pixel-Schritt aufrunden + ein bisschen Padding
            l, t, r, b = bbox
            l = (l // 8) * 8
            t = (t // 8) * 8
            r = ((r + 7) // 8) * 8
            b = ((b + 7) // 8) * 8
            # Minimum size 32x32 for nice display
            if r - l < 32:
                r = min(SHEET_SIZE, l + 32)
            if b - t < 32:
                b = min(SHEET_SIZE, t + 32)
            img = img.crop((l, t, r, b))
    return img

def _used_bbox(img):
    """Returns (left, top, right, bottom) of non-black pixels."""
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
    """Renders the map as a small image (each tile = scale pixels)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    img = Image.new("RGB", (MAP_W * scale, MAP_H * scale), (16, 16, 32))
    if not state.map_data:
        return img
    # For each map cell: use the dominant color of the sprite
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
    """Returns an average color of a sprite"""
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
                continue   # skip transparent
            r_sum += r; g_sum += g; b_sum += b; count += 1
    if count == 0:
        return (32, 32, 32)
    return (r_sum // count, g_sum // count, b_sum // count)

# ----------------------------------------------------------------------
# PDF EXPORT
# ----------------------------------------------------------------------

def export_pdf(filename, title=None, author=None):
    """Exports the current cart as a PDF manual with embedded cart."""
    missing = _check_dependencies()
    if missing:
        print(f"PDF export needs: {', '.join(missing)} (pip install {' '.join(missing)})")
        return False
    try:
        from PIL import Image  # for Pillow check
    except ImportError:
        print("PDF export needs: pillow (pip install pillow)")
        return False

    title = title or _derive_title(filename)
    author = author or "py-16 user"

    # 1) First the cart as JSON into a buffer (becomes the attachment)
    cart_buf = _build_cart_json()

    # 2) Write PDF with reportlab
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

    # 3) Embed cart as attachment via pypdf
    pdf_buf.seek(0)
    reader = PdfReader(pdf_buf)
    writer = PdfWriter(clone_from=reader)
    writer.add_attachment("cart.p16", cart_buf)

    with open(filename, "wb") as f:
        writer.write(f)
    print(f"PDF-Cart saved: {filename}")
    return True

def _derive_title(filename):
    base = os.path.basename(filename)
    if base.lower().endswith(".pdf"):
        base = base[:-4]
    return base.upper().replace("_", " ").replace("-", " ") or "UNTITLED"

def _build_cart_json():
    """Generates the cart JSON bytes (same format as .p16)."""
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

def _make_cover_image_for_style(style):
    """Returns ein PIL-Bild als Cover, depending vom Stil:
    'sheet'      = sprite sheet (cropped to used area)
    'map'        = color map overview (scaled up)
    'screenshot' = screenshot of the current engine screen
    'custom'     = custom image (embedded in cart as base64)"""
    if style == "custom":
        return _decode_custom_image() or _make_sprite_sheet_image(crop_to_used=True)
    if style == "screenshot":
        return _make_screenshot_image()
    if style == "map":
        return _make_map_image(scale=4)
    return _make_sprite_sheet_image(crop_to_used=True)

def _make_screenshot_image():
    """Creates a screenshot of the current state.screen as a PIL image."""
    try:
        from PIL import Image
    except ImportError:
        return None
    if state.screen is None:
        return None
    import pygame
    if _HAS_NUMPY:
        arr = pygame.surfarray.array3d(state.screen)
        arr = arr.transpose(1, 0, 2)
        return Image.fromarray(arr.astype("uint8"))
    else:
        w, h = state.screen.get_size()
        img = Image.new("RGB", (w, h))
        for y in range(h):
            for x in range(w):
                img.putpixel((x, y), tuple(state.screen.get_at((x, y))[:3]))
        return img

# ----------------------------------------------------------------------
# COVER-SETTINGS
# ----------------------------------------------------------------------

# Map each family to a 4-tuple: (regular, bold, italic, bold_italic).
# These are the standard 14 PDF fonts; ReportLab knows them by name.
FONT_FAMILIES = {
    "helvetica": ("Helvetica", "Helvetica-Bold",
                  "Helvetica-Oblique", "Helvetica-BoldOblique"),
    "courier":   ("Courier", "Courier-Bold",
                  "Courier-Oblique", "Courier-BoldOblique"),
    "times":     ("Times-Roman", "Times-Bold",
                  "Times-Italic", "Times-BoldItalic"),
    # "pixel" is not a real PDF font; we map it to Courier-Bold (monospace)
    "pixel":     ("Courier-Bold", "Courier-Bold",
                  "Courier-BoldOblique", "Courier-BoldOblique"),
}

DEFAULT_COVER = {
    "color_bg":          1,    # Pico dark blue
    "color_band":        14,   # Pico pink
    "color_title_text":  0,    # black
    "color_author_text": 7,    # white
    "font":              "helvetica",
    "custom_image":      None,
    # Title styling
    "title_size":        32,
    "title_bold":        True,
    "title_italic":      False,
    "title_underline":   False,
    # Author styling
    "author_size":       10,
    "author_bold":       True,
    "author_italic":     False,
    "author_underline":  False,
}

def _cover_settings():
    """Returns Cover-Setting-Dict, gefuellt aus cart_meta + defaults."""
    meta = getattr(state, "cart_meta", {}) or {}
    s = dict(DEFAULT_COVER)
    for k in DEFAULT_COVER:
        if k in meta and meta[k] is not None:
            s[k] = meta[k]
    return s

def _palette_to_rgb_normalized(idx):
    """Wandelt Paletten-Index 0-255 in (r,g,b) mit 0..1-Werten."""
    from .core import PALETTE
    if 0 <= idx < len(PALETTE):
        r, g, b = PALETTE[idx]
        return (r/255, g/255, b/255)
    return (0, 0, 0)

def _font_for(s, weight="regular"):
    """Returns the ReportLab font name for the setting.

    weight: "regular", "bold", "oblique", or "bold_oblique"."""
    family = s.get("font", "helvetica")
    fonts = FONT_FAMILIES.get(family, FONT_FAMILIES["helvetica"])
    idx = {"regular": 0, "bold": 1, "oblique": 2, "bold_oblique": 3}.get(weight, 0)
    return fonts[idx]

def _font_variant(s, bold, italic):
    """Build the right font variant from bold/italic flags."""
    if bold and italic:
        return _font_for(s, "bold_oblique")
    if bold:
        return _font_for(s, "bold")
    if italic:
        return _font_for(s, "oblique")
    return _font_for(s, "regular")

def _draw_text_styled(c, text, x, y, font_name, font_size, underline=False,
                      centered=True):
    """Draw text with optional underline. ReportLab has no native underline
    so we measure the string width and draw a line below it.

    If centered=True, x is the center; else x is the left edge."""
    c.setFont(font_name, font_size)
    if centered:
        c.drawCentredString(x, y, text)
    else:
        c.drawString(x, y, text)

    if not underline or not text:
        return

    # Measure the string and draw a line below
    from reportlab.pdfbase.pdfmetrics import stringWidth
    width = stringWidth(text, font_name, font_size)
    underline_y = y - font_size * 0.18   # slight gap below baseline
    line_thickness = max(0.5, font_size * 0.04)
    if centered:
        x0 = x - width / 2
    else:
        x0 = x
    c.setLineWidth(line_thickness)
    c.line(x0, underline_y, x0 + width, underline_y)

def _decode_custom_image():
    """Wandelt das base64-embedded Custom-Bild in ein PIL-Image um.
    Returns None wenn nicht gesets oder Fehler."""
    s = _cover_settings()
    data_b64 = s.get("custom_image")
    if not data_b64:
        return None
    try:
        from PIL import Image
        import base64
        raw = base64.b64decode(data_b64)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as e:
        print(f"Custom image decode failed: {e}")
        return None

def _draw_cover(c, w, h, title, author):
    """Cover page in box style with configurable colors/fonts."""
    s = _cover_settings()

    # Background (from palette index)
    bg_rgb = _palette_to_rgb_normalized(s["color_bg"])
    c.setFillColorRGB(*bg_rgb)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Title band on top
    band_rgb = _palette_to_rgb_normalized(s["color_band"])
    c.setFillColorRGB(*band_rgb)
    c.rect(0, h - 80*mm, w, 30*mm, fill=1, stroke=0)

    # Title text on the band
    title_rgb = _palette_to_rgb_normalized(s["color_title_text"])
    c.setFillColorRGB(*title_rgb)
    title_font = _font_variant(s, s["title_bold"], s["title_italic"])
    _draw_text_styled(c, title, w / 2, h - 65*mm,
                      title_font, s["title_size"],
                      underline=s["title_underline"], centered=True)

    # Subtitle (engine name) - this stays as our fixed style
    c.setFont(_font_for(s, "regular"), 12)
    c.drawCentredString(w / 2, h - 75*mm, "PY-16 FANTASY CONSOLE CARTRIDGE")

    # Cover-Bild depending vom gechoosesen Stil
    cover_style = (state.cart_meta or {}).get("cover_style", "sheet") \
        if hasattr(state, "cart_meta") else "sheet"

    img = _make_cover_image_for_style(cover_style)
    if img is not None:
        # Replace black (transparent) pixels with cover background color,
        # so sprite transparency doesn't appear as black holes
        try:
            from PIL import Image
            from .core import PALETTE
            bg_idx = s["color_bg"]
            bg_color = tuple(PALETTE[bg_idx]) if 0 <= bg_idx < len(PALETTE) else (29, 43, 83)
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
        # Upscale at pixel level with nearest neighbor (4x)
        upscale = 4
        big = img.resize((cw * upscale, ch * upscale), 0)
        img_buf = io.BytesIO()
        big.save(img_buf, format="PNG")
        img_buf.seek(0)
        from reportlab.lib.utils import ImageReader

        # Max display size: 130mm width OR 130mm height
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

    # Footer: author + date with configurable styling
    author_rgb = _palette_to_rgb_normalized(s["color_author_text"])
    c.setFillColorRGB(*author_rgb)
    author_font = _font_variant(s, s["author_bold"], s["author_italic"])
    _draw_text_styled(c, f"BY {author.upper()}", w / 2, 30*mm,
                      author_font, s["author_size"],
                      underline=s["author_underline"], centered=True)
    c.setFont(_font_for(s, "regular"), 9)
    today = datetime.date.today().isoformat()
    c.drawCentredString(w / 2, 22*mm, today)
    c.setFont(_font_for(s, "oblique"), 8)
    c.drawCentredString(w / 2, 14*mm,
                        "OPEN THIS PDF WITH PY-16 TO PLAY")

# ----------------------------------------------------------------------
# MANUAL-PAGE (aus @manual-Kommentar)
# ----------------------------------------------------------------------

def _draw_manual_page(c, w, h, title, sections):
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Header
    c.setFillColorRGB(0.1, 0.15, 0.3)
    c.rect(0, h - 25*mm, w, 25*mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20*mm, h - 17*mm, title + " - MANUAL")

    y = h - 40*mm
    c.setFillColorRGB(0, 0, 0)

    if sections.get("description"):
        c.setFont("Helvetica-Bold", 13)
        c.drawString(20*mm, y, "DESCRIPTION")
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
        c.drawString(20*mm, y, "CONTROLS")
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
# ASSET-PAGE
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

        # Light gray background for listing
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
# PDF LADEN (Cart-attachment extrahieren)
# ----------------------------------------------------------------------

def load_pdf(filename):
    """Read a py-16 PDF cart and extract the embedded .p16 attachment."""
    if not _HAS_PYPDF:
        print("PDF loading needs: pypdf (pip install pypdf)")
        return False
    if not os.path.exists(filename):
        print(f"PDF '{filename}' not found")
        return False

    reader = PdfReader(filename)
    attachments = reader.attachments
    if not attachments:
        print(f"'{os.path.basename(filename)}' is a regular PDF "
              f"(no py-16 cart embedded)")
        return False

    # Look for cart.p16 specifically (or any .p16-named attachment)
    cart_data = None
    for name, content_list in attachments.items():
        if name.lower().endswith(".p16") or name.lower() == "cart.p16":
            cart_data = content_list[0] if isinstance(content_list, list) else content_list
            break

    if cart_data is None:
        # No .p16 attachment - this is probably a regular PDF that
        # happens to have unrelated attachments (e.g. preview images).
        # Don't try to load arbitrary content as a cart.
        print(f"'{os.path.basename(filename)}' has attachments but none "
              f"named *.p16 (probably not a py-16 cart)")
        return False

    # Verify the attachment looks like a py-16 cart (JSON starting with '{')
    if not cart_data or not cart_data.lstrip().startswith(b"{"):
        print(f"'{os.path.basename(filename)}' has a .p16 attachment but "
              f"its content is not valid py-16 cart JSON")
        return False

    # Inspect the cart JSON for an empty code field, since that's a
    # common failure mode (PDF saved before any code was written).
    try:
        import json as _json
        cart_json = _json.loads(cart_data)
        code_text = cart_json.get("code", "")
        if not code_text or not code_text.strip():
            print(f"'{os.path.basename(filename)}' is a py-16 cart but "
                  f"has no code (empty cart - open in F6 editor to write some)")
            # Still load it so the user lands in a usable state, but
            # leave the cart_code empty so the runtime can show a clear
            # 'empty cart' message instead of fishing for update/draw.
    except Exception:
        # JSON parse failed - fall through, load_cart will report the
        # real error.
        pass

    # Write temporarily and load via the .p16 loader
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
        print(f"PDF-Cart loaded: {filename}")
    return ok
