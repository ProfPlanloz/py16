"""
py16.pdf_export
===============
Exportiert einen Cart als PDF-Handbuch mit eingebettetem .p16-Cart.

Die generierte PDF enthaelt:
  1. Cover mit Titel und Sprite-Sheet
  2. Spielanleitung (aus @manual...@end-Block im Code)
  3. Asset-Listing (Sprite-Sheet, Map, SFX-Uebersicht)
  4. Code-Listing mit Zeilennummern
  5. cart.p16 als Datei-Anhang

Der Cart kann mit `import_pdf()` aus der PDF zurueckgewonnen werden.

Optionale Abhaengigkeiten:
  reportlab  -  fuer Export
  pypdf      -  fuer Import / Cart-Anhang lesen
"""

import os
import io
import re
import json
import base64
import datetime

from . import state, sfx_data
from .core import PALETTE, SHEET_SIZE, SPRITES_PER_ROW, SPRITE_PIX, MAP_W, MAP_H
from .cart import save_cart

# ----------------------------------------------------------------------
# REPORTLAB-IMPORT (optional)
# ----------------------------------------------------------------------

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

try:
    import pypdf
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False

try:
    from PIL import Image as PILImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# ----------------------------------------------------------------------
# KONSTANTEN
# ----------------------------------------------------------------------

PAGE_W, PAGE_H = A4 if _HAS_REPORTLAB else (595, 842)
MARGIN = 18 * mm if _HAS_REPORTLAB else 50

# Box-Stil: Hintergrund-Rahmen-Farbe, Dunkelblau wie ein Spieleboxrand
BOX_BORDER = "#1d2b53"   # = Pico-Palette[1]
BOX_ACCENT = "#7e2553"   # = Pico-Palette[2]
TEXT_DARK  = "#000000"
TEXT_LIGHT = "#5f574f"

# ----------------------------------------------------------------------
# HELPER: SPRITE-SHEET ALS PIL-IMAGE
# ----------------------------------------------------------------------

def _sheet_to_pil_image(scale=4):
    """Konvertiert das Sprite-Sheet in ein PIL.Image fuer reportlab."""
    if not _HAS_PIL:
        raise RuntimeError("PIL/Pillow fuer Bild-Export benoetigt: pip install Pillow")
    import pygame
    arr = pygame.surfarray.array3d(state.sprite_sheet)
    arr = arr.transpose(1, 0, 2)  # pygame: (W,H,3) -> PIL: (H,W,3)
    img = PILImage.fromarray(arr.astype("uint8"))
    if scale > 1:
        img = img.resize(
            (img.width * scale, img.height * scale),
            PILImage.NEAREST
        )
    return img

def _map_overview_pil_image(scale=2):
    """Rendert eine Map-Uebersicht als kleines PIL-Image."""
    if not _HAS_PIL:
        raise RuntimeError("PIL/Pillow benoetigt")
    import pygame
    # 128x128 Tiles -> 1024x1024 Pixel waere zu groß, also 1 Pixel pro Tile
    img = PILImage.new("RGB", (MAP_W, MAP_H), (0, 0, 0))
    pixels = img.load()
    for y in range(MAP_H):
        for x in range(MAP_W):
            sid = state.map_data[y][x]
            if sid > 0:
                # Mittlere Farbe des Sprites bestimmen
                sx = (sid % SPRITES_PER_ROW) * SPRITE_PIX + 4
                sy = (sid // SPRITES_PER_ROW) * SPRITE_PIX + 4
                rgb = tuple(state.sprite_sheet.get_at((sx, sy))[:3])
                pixels[x, y] = rgb
    if scale > 1:
        img = img.resize(
            (img.width * scale, img.height * scale),
            PILImage.NEAREST
        )
    return img

def _pil_to_imagereader(img):
    """PIL.Image -> reportlab.ImageReader (via In-Memory-PNG)."""
    from reportlab.lib.utils import ImageReader
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)

# ----------------------------------------------------------------------
# MANUAL-EXTRAKTION AUS CODE
# ----------------------------------------------------------------------

_MANUAL_RE = re.compile(
    r"#\s*@manual\s*\n(.*?)\n\s*#\s*@end",
    re.DOTALL | re.IGNORECASE,
)

def _extract_manual(code_text):
    """Extrahiert den @manual...@end-Block aus dem Code.
    Entfernt fuehrende '#'-Zeichen Zeile fuer Zeile."""
    m = _MANUAL_RE.search(code_text)
    if not m:
        return None
    raw = m.group(1)
    cleaned = []
    for line in raw.splitlines():
        # Fuehrende '#' und Whitespace entfernen
        s = line.lstrip()
        if s.startswith("#"):
            s = s[1:]
        cleaned.append(s.rstrip())
    return "\n".join(cleaned).strip()

def _extract_title(code_text):
    """Sucht eine Titel-Zeile in @manual: erste nicht-leere Zeile."""
    manual = _extract_manual(code_text) or ""
    for line in manual.splitlines():
        line = line.strip()
        if line:
            return line
    return None

# ----------------------------------------------------------------------
# PDF-SEITEN
# ----------------------------------------------------------------------

def _draw_cover(c, title, subtitle, sheet_img):
    """Cover im Spielebox-Stil."""
    # Hintergrund-Farbverlauf imitieren (zwei Boxen)
    c.setFillColor(HexColor(BOX_BORDER))
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Innerer Rahmen
    inset = 12 * mm
    c.setFillColor(HexColor("#000000"))
    c.rect(inset, inset, PAGE_W - 2*inset, PAGE_H - 2*inset, fill=1, stroke=0)

    # Akzent-Streifen oben und unten
    c.setFillColor(HexColor(BOX_ACCENT))
    c.rect(inset, PAGE_H - inset - 8*mm, PAGE_W - 2*inset, 8*mm, fill=1, stroke=0)
    c.rect(inset, inset, PAGE_W - 2*inset, 8*mm, fill=1, stroke=0)

    # Engine-Text oben
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inset + 4*mm, PAGE_H - inset - 5.5*mm, "PY-16 FANTASY CONSOLE")
    c.setFont("Helvetica", 9)
    c.drawRightString(PAGE_W - inset - 4*mm, PAGE_H - inset - 5.5*mm,
                       datetime.datetime.now().strftime("%Y-%m-%d"))

    # Sprite-Sheet als zentrales Bild (groß, gerastert)
    img_size = 100 * mm
    img_x = (PAGE_W - img_size) / 2
    img_y = PAGE_H / 2 - img_size / 2 + 10*mm
    # Rahmen um das Bild
    c.setStrokeColor(HexColor("#ffffff"))
    c.setLineWidth(1)
    c.rect(img_x - 2, img_y - 2, img_size + 4, img_size + 4, fill=0, stroke=1)
    if sheet_img is not None:
        reader = _pil_to_imagereader(sheet_img)
        c.drawImage(reader, img_x, img_y, img_size, img_size,
                    preserveAspectRatio=True, mask='auto')

    # Titel unten
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(PAGE_W / 2, img_y - 18*mm, title)

    if subtitle:
        c.setFont("Helvetica", 12)
        c.drawCentredString(PAGE_W / 2, img_y - 26*mm, subtitle)

    # Footer
    c.setFont("Helvetica", 8)
    c.drawCentredString(PAGE_W / 2, inset + 3*mm,
                        "Cart als Anhang in dieser PDF eingebettet (cart.p16)")

    c.showPage()

def _draw_manual_page(c, manual_text):
    """Spielanleitung."""
    _draw_page_header(c, "SPIELANLEITUNG")
    c.setFillColor(HexColor(TEXT_DARK))
    c.setFont("Courier", 10)

    y = PAGE_H - 35 * mm
    line_h = 4.5 * mm

    for line in manual_text.splitlines():
        if y < MARGIN + 10*mm:
            c.showPage()
            _draw_page_header(c, "SPIELANLEITUNG (FORTS.)")
            c.setFont("Courier", 10)
            y = PAGE_H - 35 * mm
        c.drawString(MARGIN, y, line[:100])
        y -= line_h

    c.showPage()

def _draw_assets_page(c, sheet_img, map_img):
    """Sprite-Sheet und Map-Uebersicht."""
    _draw_page_header(c, "ASSETS")

    c.setFillColor(HexColor(TEXT_DARK))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN, PAGE_H - 35*mm, "Sprite-Sheet")

    if sheet_img is not None:
        sheet_size = 80 * mm
        c.setStrokeColor(HexColor(BOX_BORDER))
        c.rect(MARGIN, PAGE_H - 38*mm - sheet_size,
               sheet_size, sheet_size, fill=0, stroke=1)
        c.drawImage(_pil_to_imagereader(sheet_img),
                    MARGIN, PAGE_H - 38*mm - sheet_size,
                    sheet_size, sheet_size, mask='auto')

    # Map daneben
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN + 90*mm, PAGE_H - 35*mm, "Map-Uebersicht")

    if map_img is not None:
        map_size = 80 * mm
        c.setStrokeColor(HexColor(BOX_BORDER))
        c.rect(MARGIN + 90*mm, PAGE_H - 38*mm - map_size,
               map_size, map_size, fill=0, stroke=1)
        c.drawImage(_pil_to_imagereader(map_img),
                    MARGIN + 90*mm, PAGE_H - 38*mm - map_size,
                    map_size, map_size, mask='auto')

    # Sprite-Flag-Listing darunter
    flag_y = PAGE_H - 38*mm - 80*mm - 12*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN, flag_y, "Sprite-Flags (nur belegte)")

    flag_y -= 6*mm
    c.setFont("Courier", 8)
    flagged = [(i, f) for i, f in enumerate(state.sprite_flags) if f]
    col_w = 40 * mm
    for idx, (sid, f) in enumerate(flagged[:60]):
        col = idx % 4
        row = idx // 4
        x = MARGIN + col * col_w
        y = flag_y - row * 4 * mm
        if y < MARGIN:
            break
        flag_str = "".join("1" if f & (1 << b) else "." for b in range(8))
        c.drawString(x, y, f"#{sid:04d}  {flag_str}")

    c.showPage()

def _draw_audio_page(c):
    """SFX und Music-Uebersicht."""
    _draw_page_header(c, "AUDIO")
    c.setFillColor(HexColor(TEXT_DARK))

    if not hasattr(state, "sfx_patches"):
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN, PAGE_H - 35*mm, "Keine Audio-Daten vorhanden.")
        c.showPage()
        return

    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN, PAGE_H - 35*mm, "SFX-Patches (belegte)")

    y = PAGE_H - 42*mm
    c.setFont("Courier", 8)
    line_h = 3.5 * mm

    for i, patch in enumerate(state.sfx_patches):
        # Nur Patches mit mindestens einer aktiven Note zeigen
        active_notes = [n for n in patch["notes"] if n[0] != sfx_data.NOTE_EMPTY]
        if not active_notes:
            continue
        if y < MARGIN + 10*mm:
            c.showPage()
            _draw_page_header(c, "AUDIO (FORTS.)")
            c.setFont("Courier", 8)
            y = PAGE_H - 35*mm

        # Noten-String generieren
        notes_str = "".join(
            sfx_data.note_name(n[0]).replace("-", "") if n[0] != sfx_data.NOTE_EMPTY else "  "
            for n in patch["notes"][:16]
        )
        c.drawString(MARGIN, y,
                     f"#{i:02d}  speed={patch['speed']:02d}  notes:{notes_str}")
        y -= line_h

    # Music-Tracks
    if any(state.music_tracks):
        y -= 5*mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(MARGIN, y, "Music-Tracks")
        y -= 6*mm
        c.setFont("Courier", 8)
        for i, track in enumerate(state.music_tracks):
            if not track:
                continue
            if y < MARGIN + 10*mm:
                c.showPage()
                _draw_page_header(c, "AUDIO (FORTS.)")
                c.setFont("Courier", 8)
                y = PAGE_H - 35*mm
            seq = " > ".join(f"P{p:02d}" for p in track[:20])
            c.drawString(MARGIN, y, f"Track {i}:  {seq}")
            y -= line_h

    c.showPage()

def _draw_code_listing(c, code_text):
    """Code-Listing mit Zeilennummern."""
    _draw_page_header(c, "CODE-LISTING")

    lines = code_text.splitlines() or [""]
    c.setFillColor(HexColor(TEXT_DARK))
    c.setFont("Courier", 8)

    line_h = 3.3 * mm
    gutter_w = 12 * mm
    page_lines = int((PAGE_H - 40*mm) / line_h)

    for batch_start in range(0, len(lines), page_lines):
        batch = lines[batch_start:batch_start + page_lines]
        y = PAGE_H - 35*mm

        for i, line in enumerate(batch):
            line_no = batch_start + i + 1
            # Zeilennummer in grau
            c.setFillColor(HexColor("#888888"))
            c.drawRightString(MARGIN + gutter_w - 2, y, f"{line_no:4d}")
            # Trennlinie zwischen Gutter und Code
            c.setStrokeColor(HexColor("#cccccc"))
            c.line(MARGIN + gutter_w, y - 1, MARGIN + gutter_w, y + 3)
            # Code
            c.setFillColor(HexColor(TEXT_DARK))
            # Tabs durch 4 Spaces ersetzen, lange Zeilen abschneiden
            display = line.replace("\t", "    ")[:90]
            # Funktions-Header etwas hervorheben
            if display.lstrip().startswith(("def ", "class ")):
                c.setFont("Courier-Bold", 8)
                c.drawString(MARGIN + gutter_w + 2, y, display)
                c.setFont("Courier", 8)
            else:
                c.drawString(MARGIN + gutter_w + 2, y, display)
            y -= line_h

        if batch_start + page_lines < len(lines):
            c.showPage()
            _draw_page_header(c, "CODE-LISTING (FORTS.)")
            c.setFont("Courier", 8)

    c.showPage()

def _draw_page_header(c, title):
    """Seitenkopf: Titel oben, Trennlinie."""
    c.setFillColor(HexColor(BOX_BORDER))
    c.rect(0, PAGE_H - 22*mm, PAGE_W, 12*mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN, PAGE_H - 16*mm, title)
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 16*mm, "py-16")

# ----------------------------------------------------------------------
# OEFFENTLICHE API
# ----------------------------------------------------------------------

def export_pdf(filename="cart.pdf", title=None, subtitle=None):
    """Exportiert den aktuellen Cart als PDF mit eingebettetem cart.p16.

    title/subtitle sind optional - wenn nicht angegeben, wird aus dem
    @manual-Block der erste nicht-leere Eintrag genommen.
    """
    if not _HAS_REPORTLAB:
        raise RuntimeError(
            "reportlab nicht installiert. Bitte: pip install reportlab Pillow"
        )
    if not _HAS_PIL:
        raise RuntimeError(
            "Pillow nicht installiert. Bitte: pip install Pillow"
        )

    code_text = getattr(state, "cart_code", "") or ""

    # Titel aus Manual-Block ableiten
    if title is None:
        title = _extract_title(code_text) or "UNTITLED CART"
    if subtitle is None:
        subtitle = state.cart_code_file or "py-16 cart"
        # nur Dateiname statt Pfad
        subtitle = os.path.basename(subtitle) if subtitle else "py-16 cart"

    # Bilder vorbereiten
    sheet_img = _sheet_to_pil_image(scale=2)
    map_img = _map_overview_pil_image(scale=2)

    # PDF schreiben
    c = rl_canvas.Canvas(filename, pagesize=A4)
    c.setTitle(title)
    c.setAuthor("py-16")
    c.setSubject("py-16 Cart Manual")

    _draw_cover(c, title, subtitle, sheet_img)

    manual = _extract_manual(code_text)
    if manual:
        _draw_manual_page(c, manual)
    else:
        # Platzhalter-Seite, damit das Booklet konsistent bleibt
        _draw_page_header(c, "SPIELANLEITUNG")
        c.setFillColor(HexColor(TEXT_LIGHT))
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(MARGIN, PAGE_H - 40*mm,
                     "Keine Spielanleitung vorhanden.")
        c.drawString(MARGIN, PAGE_H - 45*mm,
                     "Tipp: Schreibe einen # @manual ... # @end-Block")
        c.drawString(MARGIN, PAGE_H - 50*mm,
                     "in deinen Code, um hier eine Anleitung zu erzeugen.")
        c.showPage()

    _draw_assets_page(c, sheet_img, map_img)
    _draw_audio_page(c)
    _draw_code_listing(c, code_text)

    # Cart als Datei-Anhang einbetten
    # Wir speichern erst eine temporaere .p16 und haengen sie dann an
    cart_bytes = _build_cart_bytes()
    c.embed_file(cart_bytes, filename="cart.p16",
                 mimeType="application/octet-stream",
                 description="py-16 Cart-Datei (JSON)")

    c.save()
    print(f"PDF exportiert: {filename}")

def _build_cart_bytes():
    """Erzeugt die Cart-Bytes im Speicher (ohne Datei zu schreiben)."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".p16",
                                     delete=False) as f:
        tmp = f.name
    try:
        save_cart(tmp)
        with open(tmp, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

def import_pdf(filename, target_p16=None):
    """Reads the embedded cart.p16 from a PDF and loads it.

    If target_p16 is given, the cart is also written there as a .p16 file.
    """
    if not _HAS_PYPDF:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")
    if not os.path.exists(filename):
        raise FileNotFoundError(filename)

    reader = pypdf.PdfReader(filename)
    attachments = reader.attachments

    # Look for cart.p16 (or the first .p16 attachment)
    cart_data = None
    cart_name = None
    for name, datas in attachments.items():
        # pypdf returns datas as a list of byte streams
        data = datas[0] if isinstance(datas, list) else datas
        if name.endswith(".p16"):
            cart_data = data
            cart_name = name
            break
    if cart_data is None and attachments:
        # Fallback: take the first attachment
        first = next(iter(attachments.items()))
        cart_name = first[0]
        cart_data = first[1][0] if isinstance(first[1], list) else first[1]

    if cart_data is None:
        raise ValueError(f"No cart attachments found in {filename}")

    # Load cart
    if target_p16:
        with open(target_p16, "wb") as f:
            f.write(cart_data)
        from .cart import load_cart
        load_cart(target_p16)
    else:
        # Load directly from memory via tempfile
        import tempfile
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".p16",
                                         delete=False) as f:
            f.write(cart_data)
            tmp = f.name
        try:
            from .cart import load_cart
            load_cart(tmp)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    print(f"Cart loaded from PDF: {cart_name}")
    return True
