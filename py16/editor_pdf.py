"""
py16.editor_pdf
================
PDF-Editor (F7). Live-preview plus editierbare Cover-data.

Tab METADATA: Titel, Autor, Cover-Stil
Tab STYLE:     4 colors (BG, band, title text, author text) + font
Tab IMAGE:     Path to custom image (PNG/JPG, embedded in cart)

controls:
  Q / W / Tab        Switch tab
  Arrow up/down       Choose field
  Arrow left/right    Adjust value (style/font/colors)
  Letters/digits      Text input
  Backspace           Delete character
  Ctrl+L             Load image from path
  Ctrl+S             Save as .p16 AND .pdf
  ESC / F7           Close editor
"""

import os
import io
import base64
import pygame

from . import state
from .core import WIDTH, HEIGHT, SHEET_SIZE
from .graphics import cls, rectfill, rect, line, text
from .input import btn, btnp

# ----------------------------------------------------------------------
# KONSTANTEN
# ----------------------------------------------------------------------

COVER_STYLES = ["sheet", "map", "screenshot", "custom"]
FONTS = ["helvetica", "courier", "times", "pixel"]

TABS = ["META", "STIL", "BILD"]

FIELDS_META  = ["title", "author", "cover_style"]
FIELDS_STYLE = ["color_bg", "color_band",
                "color_title_text", "color_author_text", "font"]
FIELDS_IMAGE = ["custom_image_path"]

MAX_IMAGE_BYTES = 200 * 1024

# ----------------------------------------------------------------------
# STATE
# ----------------------------------------------------------------------

def _ensure_state():
    defaults = {
        "pe_title":             "",
        "pe_author":            "",
        "pe_cover_style":       "sheet",
        "pe_color_bg":          1,
        "pe_color_band":        14,
        "pe_color_title_text":  0,
        "pe_color_author_text": 7,
        "pe_font":              "helvetica",
        "pe_custom_image":      None,
        "pe_custom_image_path": "",

        "pe_tab":               0,
        "pe_field":             0,
        "pe_status":            "",
        "pe_status_color":      7,
        "pe_status_time":       0,
        "pe_screenshot":        None,
        "pe_initialized_for":   None,
    }
    for k, v in defaults.items():
        if not hasattr(state, k):
            setattr(state, k, v)

def _on_open():
    _ensure_state()
    cur_file = getattr(state, "cart_code_file", None)
    if state.pe_initialized_for == cur_file:
        return

    meta = getattr(state, "cart_meta", {}) or {}
    state.pe_title         = meta.get("title", _derive_default_title())
    state.pe_author        = meta.get("author", "")
    state.pe_cover_style   = meta.get("cover_style", "sheet")
    state.pe_color_bg          = meta.get("color_bg",          1)
    state.pe_color_band        = meta.get("color_band",        14)
    state.pe_color_title_text  = meta.get("color_title_text",  0)
    state.pe_color_author_text = meta.get("color_author_text", 7)
    state.pe_font          = meta.get("font", "helvetica")
    state.pe_custom_image  = meta.get("custom_image", None)
    state.pe_custom_image_path = ""
    state.pe_initialized_for = cur_file

    if state.screen is not None:
        state.pe_screenshot = state.screen.copy()

def _derive_default_title():
    src = getattr(state, "cart_code_file", None) or "untitled"
    base = os.path.splitext(os.path.basename(src))[0]
    return base.upper().replace("_", " ").replace("-", " ")

def _set_status(msg, color=7):
    state.pe_status = msg
    state.pe_status_color = color
    state.pe_status_time = state.frame_count

def _current_tab_fields():
    return [FIELDS_META, FIELDS_STYLE, FIELDS_IMAGE][state.pe_tab]

def _just_pressed(key):
    return state.keys.get(key, False) and not state.keys_prev.get(key, False)

# ----------------------------------------------------------------------
# UPDATE
# ----------------------------------------------------------------------

def pdf_editor_update():
    _ensure_state()
    ctrl  = state.keys.get(pygame.K_LCTRL, False) or state.keys.get(pygame.K_RCTRL, False)
    shift = state.keys.get(pygame.K_LSHIFT, False) or state.keys.get(pygame.K_RSHIFT, False)

    if ctrl and _just_pressed(pygame.K_s):
        _save_with_meta()
        return
    if ctrl and _just_pressed(pygame.K_l):
        _load_custom_image()
        return

    if _just_pressed(pygame.K_q):
        state.pe_tab = (state.pe_tab - 1) % len(TABS)
        state.pe_field = 0
        return
    if _just_pressed(pygame.K_w):
        state.pe_tab = (state.pe_tab + 1) % len(TABS)
        state.pe_field = 0
        return
    if _just_pressed(pygame.K_TAB):
        state.pe_tab = (state.pe_tab + (-1 if shift else 1)) % len(TABS)
        state.pe_field = 0
        return

    fields = _current_tab_fields()
    if btnp('up'):
        state.pe_field = max(0, state.pe_field - 1)
        return
    if btnp('down'):
        state.pe_field = min(len(fields) - 1, state.pe_field + 1)
        return

    field_name = fields[state.pe_field]
    _handle_field_input(field_name, shift)

def _handle_field_input(field, shift):
    if field == "cover_style":
        if btnp('left'):
            i = COVER_STYLES.index(state.pe_cover_style)
            state.pe_cover_style = COVER_STYLES[(i - 1) % len(COVER_STYLES)]
        elif btnp('right'):
            i = COVER_STYLES.index(state.pe_cover_style)
            state.pe_cover_style = COVER_STYLES[(i + 1) % len(COVER_STYLES)]
        return

    if field == "font":
        if btnp('left'):
            i = FONTS.index(state.pe_font)
            state.pe_font = FONTS[(i - 1) % len(FONTS)]
        elif btnp('right'):
            i = FONTS.index(state.pe_font)
            state.pe_font = FONTS[(i + 1) % len(FONTS)]
        return

    if field.startswith("color_"):
        attr = "pe_" + field
        cur = getattr(state, attr)
        if btnp('left'):
            setattr(state, attr, (cur - 1) % 256)
        elif btnp('right'):
            setattr(state, attr, (cur + 1) % 256)
        if _just_pressed(pygame.K_PAGEUP):
            setattr(state, attr, (cur - 16) % 256)
        elif _just_pressed(pygame.K_PAGEDOWN):
            setattr(state, attr, (cur + 16) % 256)
        return

    if field in ("title", "author", "custom_image_path"):
        attr = "pe_" + field
        if _just_pressed(pygame.K_BACKSPACE):
            setattr(state, attr, getattr(state, attr)[:-1])
            return
        for k in list(state.keys.keys()):
            if state.keys.get(k, False) and not state.keys_prev.get(k, False):
                ch = _key_to_char(k, shift)
                if ch:
                    val = getattr(state, attr)
                    max_len = 200 if field == "custom_image_path" else 32
                    if len(val) < max_len:
                        setattr(state, attr, val + ch)
                    return

def _key_to_char(key, shift):
    if pygame.K_a <= key <= pygame.K_z:
        ch = chr(key)
        return ch.upper() if shift else ch
    if pygame.K_0 <= key <= pygame.K_9:
        if shift:
            return ")!@#$%^&*("[key - pygame.K_0]
        return chr(key)
    special = {
        pygame.K_SPACE:  ' ',
        pygame.K_MINUS:  '_' if shift else '-',
        pygame.K_PERIOD: '.',
        pygame.K_COMMA:  ',',
        pygame.K_SLASH:  '/',
    }
    return special.get(key)

# ----------------------------------------------------------------------
# CUSTOM-BILD LADEN
# ----------------------------------------------------------------------

def _load_custom_image():
    path = state.pe_custom_image_path.strip()
    path = os.path.expanduser(path)
    if not path:
        _set_status("NO PATH GIVEN", 8)
        return
    if not os.path.exists(path):
        _set_status(f"NOT FOUND: {os.path.basename(path)}", 8)
        return

    try:
        with open(path, "rb") as f:
            raw = f.read()
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            if img.width > 600 or img.height > 800:
                img.thumbnail((600, 800), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            png_bytes = buf.getvalue()
        except ImportError:
            png_bytes = raw

        if len(png_bytes) > MAX_IMAGE_BYTES:
            _set_status(f"IMAGE TOO LARGE: {len(png_bytes)//1024}KB > {MAX_IMAGE_BYTES//1024}KB", 8)
            return

        state.pe_custom_image = base64.b64encode(png_bytes).decode("ascii")
        state.pe_cover_style = "custom"
        _set_status(f"IMAGE LOADED: {len(png_bytes)//1024}KB", 11)
    except Exception as e:
        _set_status(f"LOAD ERROR: {e}", 8)

# ----------------------------------------------------------------------
# SAVE
# ----------------------------------------------------------------------

def _save_with_meta():
    state.cart_meta = {
        "title":             state.pe_title,
        "author":            state.pe_author,
        "cover_style":       state.pe_cover_style,
        "color_bg":          state.pe_color_bg,
        "color_band":        state.pe_color_band,
        "color_title_text":  state.pe_color_title_text,
        "color_author_text": state.pe_color_author_text,
        "font":              state.pe_font,
        "custom_image":      state.pe_custom_image,
    }
    from . import core, cart, cart_pdf
    p16_path = core._derive_cart_save_path(".p16")
    pdf_path = core._derive_cart_save_path(".pdf")

    cart.save_cart(p16_path)
    try:
        cart_pdf.export_pdf(pdf_path,
                            title=state.pe_title or None,
                            author=state.pe_author or None)
        _set_status(f"SAVED: {os.path.basename(pdf_path)}", 11)
    except Exception as e:
        _set_status(f"PDF ERROR: {e}", 8)

# ----------------------------------------------------------------------
# DRAW
# ----------------------------------------------------------------------

def pdf_editor_draw():
    _ensure_state()
    cls(0)

    rectfill(0, 0, WIDTH, 12, 13)
    text("PDF EDITOR", 4, 3, 7)
    text("CTRL-S SAVE", WIDTH - 56, 3, 11)

    tab_y = 14
    rectfill(0, tab_y, WIDTH, 10, 5)
    for i, name in enumerate(TABS):
        tx = 8 + i * 50
        active = (i == state.pe_tab)
        col = 7 if active else 6
        if active:
            rectfill(tx - 2, tab_y, 44, 10, 1)
        text(name, tx, tab_y + 2, col)
    text("Q/W TABS", WIDTH - 60, tab_y + 2, 6)

    main_y = 26
    main_h = 124

    if state.pe_tab == 0:
        _draw_meta_fields(8, main_y, 116, main_h)
    elif state.pe_tab == 1:
        _draw_style_fields(8, main_y, 116, main_h)
    else:
        _draw_image_fields(8, main_y, 116, main_h)

    _draw_cover_preview(132, main_y, 116, main_h)
    _draw_manual_preview(8, main_y + main_h + 4, WIDTH - 16, 50)

    sy = HEIGHT - 16
    rectfill(0, sy, WIDTH, 16, 13)
    if state.pe_status and (state.frame_count - state.pe_status_time) < 180:
        text(state.pe_status, 4, sy + 1, state.pe_status_color)
    else:
        text("ARROWS NAV  Q/W TABS  CTRL-S SAVE", 4, sy + 1, 6)
    text("CTRL-L LOAD IMAGE  ESC EXIT", 4, sy + 9, 6)

# ---------------- TAB 0: META ----------------

def _draw_meta_fields(x, y, w, h):
    rect(x - 2, y - 2, w + 4, h + 4, 5)
    text("METADATA", x, y, 11)

    fy = y + 12
    _draw_input_field(x, fy, w, "TITLE",
                      state.pe_title, state.pe_field == 0)
    fy = y + 42
    _draw_input_field(x, fy, w, "AUTHOR",
                      state.pe_author, state.pe_field == 1)
    fy = y + 72
    _draw_select_field(x, fy, w, "COVER STYLE",
                       state.pe_cover_style, COVER_STYLES,
                       state.pe_field == 2)

    text("LEFT/RIGHT", x, y + 102, 6)
    text("CHANGES VALUE", x, y + 110, 6)

# ---------------- TAB 1: STYLE ----------------

def _draw_style_fields(x, y, w, h):
    rect(x - 2, y - 2, w + 4, h + 4, 5)
    text("COLORS & FONT", x, y, 11)

    color_fields = [
        ("BACKGROUND",  "pe_color_bg",          0),
        ("TITLE BAND",   "pe_color_band",        1),
        ("TITLE TEXT",   "pe_color_title_text",  2),
        ("AUTHOR TEXT",   "pe_color_author_text", 3),
    ]
    for label, attr, idx in color_fields:
        fy = y + 10 + idx * 22
        cur = getattr(state, attr)
        active = (state.pe_field == idx)
        _draw_color_field(x, fy, w, label, cur, active)

    fy = y + 10 + 4 * 22
    _draw_select_field(x, fy, w, "FONT",
                       state.pe_font, FONTS,
                       state.pe_field == 4)

def _draw_color_field(x, y, w, label, color_idx, active):
    text(label, x, y, 6)
    box_y = y + 7
    rect(x, box_y, w, 11, 8 if active else 5)
    rectfill(x + 1, box_y + 1, w - 2, 9, 1)

    swatch_w = 16
    rectfill(x + 2, box_y + 2, swatch_w, 7, color_idx)
    rect(x + 2, box_y + 2, swatch_w, 7, 7)

    text(f"#{color_idx:03d}", x + swatch_w + 6, box_y + 3, 7)
    if active:
        text("<", x + w - 14, box_y + 3, 7)
        text(">", x + w - 6, box_y + 3, 7)

# ---------------- TAB 2: IMAGE ----------------

def _draw_image_fields(x, y, w, h):
    rect(x - 2, y - 2, w + 4, h + 4, 5)
    text("CUSTOM IMAGE", x, y, 11)

    fy = y + 12
    _draw_input_field(x, fy, w, "PATH TO PNG/JPG",
                      state.pe_custom_image_path,
                      state.pe_field == 0,
                      max_visible=22)

    fy2 = y + 50
    if state.pe_custom_image:
        text("IMAGE EMBEDDED", x, fy2, 11)
        kb = len(state.pe_custom_image) * 3 // 4 // 1024
        text(f"GROESSE: {kb:3d}KB", x, fy2 + 8, 6)
    else:
        text("NO IMAGE LOADED", x, fy2, 8)

    text("CTRL-L LOADS IMAGE", x, y + 78, 6)
    text("FROM PATH INTO CART", x, y + 86, 6)
    text("MAX 200KB", x, y + 96, 6)
    text("EXAMPLE:", x, y + 108, 6)
    text("~/COVER.PNG", x, y + 116, 7, upper=False)

# ---------------- COVER PREVIEW ----------------

def _draw_cover_preview(x, y, w, h):
    rect(x - 2, y - 2, w + 4, h + 4, 5)
    text("LIVE COVER", x, y, 11)

    cy = y + 12
    cw = w
    ch = h - 12

    rectfill(x, cy, cw, ch, state.pe_color_bg)
    rectfill(x, cy, cw, 14, state.pe_color_band)
    title = state.pe_title or "UNTITLED"
    short = title[:18]
    title_x = x + (cw - len(short) * 4) // 2
    text(short, title_x, cy + 4, state.pe_color_title_text)

    inner_x = x + 6
    inner_y = cy + 18
    inner_w = cw - 12
    inner_h = ch - 32

    if state.pe_cover_style == "sheet":
        _preview_sheet(inner_x, inner_y, inner_w, inner_h)
    elif state.pe_cover_style == "map":
        _preview_map(inner_x, inner_y, inner_w, inner_h)
    elif state.pe_cover_style == "screenshot":
        _preview_screenshot(inner_x, inner_y, inner_w, inner_h)
    elif state.pe_cover_style == "custom":
        _preview_custom(inner_x, inner_y, inner_w, inner_h)

    author = state.pe_author or "ANONYMOUS"
    author_text = f"BY {author}"[:22]
    ax = x + (cw - len(author_text) * 4) // 2
    text(author_text, ax, cy + ch - 9, state.pe_color_author_text)

def _preview_sheet(x, y, w, h):
    if state.sprite_sheet is None:
        return
    sheet_size = min(SHEET_SIZE, 64)
    sub = state.sprite_sheet.subsurface((0, 0, sheet_size, sheet_size // 2))
    scaled = pygame.transform.scale(sub, (w, h))
    state.screen.blit(scaled, (x, y))

def _preview_map(x, y, w, h):
    cell_w = max(1, w // 32)
    cell_h = max(1, h // 16)
    for cy in range(16):
        for cx in range(32):
            sid = state.map_data[cy + 8][cx] if state.map_data else 0
            if sid == 0:
                continue
            sx0 = (sid % 32) * 8
            sy0 = (sid // 32) * 8
            r = state.sprite_sheet.get_at((sx0 + 4, sy0 + 4))[:3]
            from .core import PALETTE
            best, bd = 0, 1 << 30
            for i, (pr, pg, pb) in enumerate(PALETTE):
                d = (r[0]-pr)**2 + (r[1]-pg)**2 + (r[2]-pb)**2
                if d < bd:
                    bd, best = d, i
            rectfill(x + cx * cell_w, y + cy * cell_h, cell_w, cell_h, best)

def _preview_screenshot(x, y, w, h):
    if state.pe_screenshot is None:
        _preview_sheet(x, y, w, h)
        rectfill(x, y + h - 10, w, 10, 0)
        text("RUN GAME FIRST", x + 2, y + h - 7, 6)
        return
    scaled = pygame.transform.scale(state.pe_screenshot, (w, h))
    state.screen.blit(scaled, (x, y))

def _preview_custom(x, y, w, h):
    if not state.pe_custom_image:
        text("NO CUSTOM IMAGE", x, y + h//2 - 4, 6)
        text("CTRL-L LOADS ONE", x, y + h//2 + 4, 6)
        return
    try:
        from PIL import Image
        raw = base64.b64decode(state.pe_custom_image)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img = img.resize((w, h), Image.LANCZOS)
        surf = pygame.image.fromstring(img.tobytes(), img.size, img.mode)
        state.screen.blit(surf, (x, y))
    except Exception:
        text("IMAGE ERROR", x, y + h//2, 8)

def _draw_manual_preview(x, y, w, h):
    rect(x - 2, y - 2, w + 4, h + 4, 5)
    text("MANUAL (READ-ONLY)", x, y, 11)
    try:
        from .cart_pdf import _extract_manual
        sections = _extract_manual(getattr(state, "cart_code", "") or "")
    except Exception:
        sections = None

    cy = y + 8
    if not sections:
        text("NO @MANUAL BLOCK", x + 4, cy + 4, 8)
        text("ADD  # @MANUAL ... # @END", x + 4, cy + 12, 6)
        return

    desc = sections.get("description", [])
    ctrls = sections.get("controls", [])
    if desc:
        text("DESC.:", x + 2, cy, 11)
        for i, ln in enumerate(desc[:2]):
            text(ln[:60], x + 2, cy + 8 * (i + 1), 7, upper=False)
    if ctrls:
        cx = x + 4
        cy2 = y + 24
        text("CONTROLS:", cx, cy2, 11)
        for i, ln in enumerate(ctrls[:3]):
            text(ln[:60], cx, cy2 + 8 * (i + 1), 6, upper=False)

# ---------------- INPUT FIELD HELPERS ----------------

def _draw_input_field(x, y, w, label, value, active, max_visible=24):
    text(label, x, y, 6)
    box_y = y + 7
    rect(x, box_y, w, 11, 8 if active else 5)
    rectfill(x + 1, box_y + 1, w - 2, 9, 1)
    display = value
    if active and (state.frame_count // 30) % 2 == 0:
        display = value + "_"
    if len(display) > max_visible:
        display = display[-max_visible:]
    text(display, x + 2, box_y + 3, 7, upper=False)

def _draw_select_field(x, y, w, label, value, options, active):
    text(label, x, y, 6)
    box_y = y + 7
    rect(x, box_y, w, 11, 8 if active else 5)
    rectfill(x + 1, box_y + 1, w - 2, 9, 1)
    arrow_color = 7 if active else 5
    text("<", x + 2, box_y + 3, arrow_color)
    text(">", x + w - 6, box_y + 3, arrow_color)
    label_x = x + (w - len(value) * 4) // 2
    text(value.upper(), label_x, box_y + 3, 7)

# ---------------- ACTIVATION ----------------

def open_editor():
    _ensure_state()
    _on_open()
    state.editor_mode = "pdf"

def toggle():
    _ensure_state()
    if state.editor_mode == "pdf":
        state.editor_mode = None
    else:
        _on_open()
        state.editor_mode = "pdf"
