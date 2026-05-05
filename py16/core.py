"""
py16.core
=========
Constants, palette, initialization and the main loop `run()`.
"""

import sys
import pygame

from . import state

# ======================================================================
# KONSTANTEN
# ======================================================================

WIDTH  = 256
HEIGHT = 224
SCALE  = 3
FPS    = 60

SHEET_SIZE      = 256
SPRITES_PER_ROW = 32
SPRITE_PIX      = 8

MAP_W = 128
MAP_H = 128

# ======================================================================
# PALETTE
# ======================================================================

_PICO_PALETTE = [
    (0, 0, 0),       (29, 43, 83),    (126, 37, 83),   (0, 135, 81),
    (171, 82, 54),   (95, 87, 79),    (194, 195, 199), (255, 241, 232),
    (255, 0, 77),    (255, 163, 0),   (255, 236, 39),  (0, 228, 54),
    (41, 173, 255),  (131, 118, 156), (255, 119, 168), (255, 204, 170),
]

def _make_default_palette():
    p = list(_PICO_PALETTE)
    for i in range(16):
        v = i * 17
        p.append((v, v, v))
    seen = set(p)
    levels = [0, 51, 102, 153, 204, 255]
    for r in levels:
        for g in levels:
            for b in levels:
                c = (r, g, b)
                if c not in seen and len(p) < 256:
                    p.append(c)
                    seen.add(c)
    while len(p) < 256:
        p.append((128, 128, 128))
    return p[:256]

PALETTE = _make_default_palette()

def color_rgb(idx):
    """Returns RGB ueber den currentn Remap."""
    return PALETTE[state.pal_remap[idx & 0xFF]]

# ======================================================================
# INIT
# ======================================================================

def _init_engine():
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        pygame.mixer.set_num_channels(8)
        state.sound_enabled = True
    except Exception as e:
        print(f"WARNUNG: Audio konnte nicht initialisiert werden: {e}")

    state.screen = pygame.Surface((WIDTH, HEIGHT))
    state.sprite_sheet = pygame.Surface((SHEET_SIZE, SHEET_SIZE))
    state.sprite_sheet.fill(PALETTE[0])
    state.sprite_sheet.set_colorkey(PALETTE[0])

    state.map_data     = [[0] * MAP_W for _ in range(MAP_H)]
    state.sprite_flags = [0] * 1024

    # Initialize tracker data
    from . import tracker
    tracker.init_tracker_state()

    # Set display mode from config
    _apply_display_mode()
    pygame.display.set_caption("py-16 Fantasy Console")
    state.clock = pygame.time.Clock()

    # Clipboard for code editor (may fail on some backends)
    try:
        pygame.scrap.init()
    except Exception:
        pass

def _compute_display_size():
    """Returns (display_w, display_h, scale_factor) based on config.
    Fullscreen: largest integer scale factor that fits.
    Windowed: fixed scale from config or default."""
    from . import config as _cfg
    cfg = _cfg.get_config()
    fullscreen = cfg.get("fullscreen", False)
    requested = cfg.get("display_scale", "auto")

    if fullscreen:
        # Determine screen size
        info = pygame.display.Info()
        screen_w, screen_h = info.current_w, info.current_h
        if requested == "auto":
            # Largest integer factor that fits
            scale = min(screen_w // WIDTH, screen_h // HEIGHT)
            scale = max(1, scale)
        else:
            try:
                scale = max(1, int(requested))
            except (ValueError, TypeError):
                scale = 1
        return screen_w, screen_h, scale
    else:
        # Windowed: requested factor or SCALE default
        if requested == "auto":
            scale = SCALE
        else:
            try:
                scale = max(1, int(requested))
            except (ValueError, TypeError):
                scale = SCALE
        return WIDTH * scale, HEIGHT * scale, scale

def _apply_display_mode():
    """Resets SDL window mode. Called at startup and on F11."""
    from . import config as _cfg
    cfg = _cfg.get_config()
    fullscreen = cfg.get("fullscreen", False)

    disp_w, disp_h, scale = _compute_display_size()
    state.display_scale = scale
    state.display_w = disp_w
    state.display_h = disp_h
    state.fullscreen = fullscreen

    flags = pygame.FULLSCREEN if fullscreen else 0
    pygame.display.set_mode((disp_w, disp_h), flags)

    # Hide mouse cursor (usually annoying in fullscreen)
    hide = cfg.get("hide_cursor", "auto")
    if hide == "auto":
        hide = fullscreen
    pygame.mouse.set_visible(not hide)

def toggle_fullscreen():
    """Toggle fullscreen at runtime."""
    from . import config as _cfg
    cfg = _cfg.get_config()
    cfg["fullscreen"] = not cfg.get("fullscreen", False)
    _apply_display_mode()

# ======================================================================
# HAUPTSCHLEIFE
# ======================================================================

def _bios_countdown(boot_path):
    """Shows a countdown screen before auto-boot.
    ESC cancels and stays in BIOS."""
    from . import config as _cfg
    from .graphics import cls as _cls, text as _text, rectfill as _rfill, rect as _rect
    import os as _os

    sec = _cfg.get_config().get("boot_countdown", 3)
    total_frames = sec * FPS
    cancelled = False

    for f in range(total_frames):
        # Read events so ESC counts
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE,):
                    cancelled = True
                else:
                    # Any other key: go to BIOS too
                    cancelled = True

        if cancelled:
            break

        _cls(1)
        _text("PY-16 FANTASY CONSOLE", 40, 60, 7)
        _text(f"AUTO-BOOT: {_os.path.basename(boot_path)}",
              40, 90, 11, upper=False)
        # Progress bar
        bar_w = 160
        progress = f / total_frames
        _rect(48, 120, bar_w, 10, 7)
        _rfill(48, 120, int(bar_w * (1 - progress)), 10, 11)
        # Remaining time
        remaining = (total_frames - f) // FPS + 1
        _text(f"{remaining}", 130, 140, 7)
        _text("ESC OR ANY KEY = BIOS", 30, 180, 6)

        scale = getattr(state, "display_scale", SCALE)
        scaled = pygame.transform.scale(state.screen,
                                        (WIDTH * scale, HEIGHT * scale))
        surf = pygame.display.get_surface()
        if getattr(state, "fullscreen", False):
            surf.fill((0, 0, 0))
            offset_x = (state.display_w - WIDTH * scale) // 2
            offset_y = (state.display_h - HEIGHT * scale) // 2
            surf.blit(scaled, (offset_x, offset_y))
        else:
            surf.blit(scaled, (0, 0))
        pygame.display.flip()
        state.clock.tick(FPS)

    if not cancelled:
        # Auto-Boot
        from . import cart_runtime
        cart_runtime.run_cart(boot_path)
        cart_runtime.process_pending_actions()
        state.bios_active = False

def _derive_cart_save_path(extension):
    """Derives a save path from the current cart context.
    Logic:
      - If cart_code_file is set and ends in .py: replace .py with .ext
      - If cart_code_file ends in .p16/.pdf: replace the extension
      - Else: <carts_dir>/untitled.<ext>
    Always returns an absolute path."""
    import os
    from . import config as _cfg

    src = getattr(state, "cart_code_file", None)
    if src:
        base, _ = os.path.splitext(src)
        return base + extension
    # Fallback: into the cart directory
    return os.path.join(_cfg.carts_dir(), "untitled" + extension)

def _save_current_cart(also_pdf=True):
    """Saves the running cart as .p16 and (if also_pdf) also as .pdf
    next to the cart source (or in carts_dir if new)."""
    from . import cart as _cart
    p16_path = _derive_cart_save_path(".p16")
    _cart.save_cart(p16_path)

    if also_pdf:
        pdf_path = _derive_cart_save_path(".pdf")
        try:
            _cart.save_cart(pdf_path)   # save_cart dispatches to PDF internally
        except Exception as e:
            print(f"PDF export failed: {e}")
            print("(PDF needs: pip install reportlab pypdf pillow pymupdf)")

def _load_current_cart():
    """Loads from the current cart path. Bevorzugt .pdf wenn vorhanden,
    sonst .p16."""
    import os
    from . import cart as _cart

    pdf_path = _derive_cart_save_path(".pdf")
    p16_path = _derive_cart_save_path(".p16")

    if os.path.exists(pdf_path):
        _cart.load_cart(pdf_path)
    elif os.path.exists(p16_path):
        _cart.load_cart(p16_path)
    else:
        print(f"No cart to load found:\n  {pdf_path}\n  {p16_path}")

def _draw_cart_load_error(err):
    """Visible cart load error screen, escape via ESC/F12/F6."""
    from .graphics import cls as _cls, text as _text, rectfill as _rfill
    _cls(0)
    # Red header
    _rfill(0, 0, WIDTH, 12, 8)
    _text("CART LOAD ERROR", 4, 3, 7)

    # Action and path
    action = err.get("action", "?")
    path = err.get("path") or "(no path)"
    short_path = path
    if len(short_path) > 60:
        short_path = "..." + short_path[-57:]
    _text(f"ACTION: {action.upper()}", 4, 18, 7)
    _text("FILE:", 4, 28, 6)
    _text(short_path, 4, 36, 7, upper=False)

    # Error text - replace newlines with spaces beforehand so lines
    # don't overlap
    msg = str(err.get("msg", "")).replace("\n", " ").replace("\r", " ")
    _text("ERROR:", 4, 52, 6)
    # Wrap error text at max ~60 chars
    line_y = 62
    for chunk_start in range(0, len(msg), 60):
        if line_y > 130:
            _text("...", 4, line_y, 8)
            break
        _text(msg[chunk_start:chunk_start + 60], 4, line_y, 8, upper=False)
        line_y += 8

    # Help at bottom
    _rfill(0, HEIGHT - 18, WIDTH, 18, 8)
    _text("ESC/F12 BIOS    F6 EDITOR    ENTER OK",
          4, HEIGHT - 13, 7)
    _text("CHECK FILE OR FIX SYNTAX",
          4, HEIGHT - 5, 7)

def run(update_func=None, draw_func=None, init_func=None):
    """main loop.
    If update_func and draw_func are None, BIOS starts.
    Otherwise the given cart runs."""
    # Lazy imports to avoid circular dependencies
    from . import editors, cart, tracker, bios, cart_runtime, config

    _init_engine()
    cart_runtime._ensure_state()
    bios._ensure_state()

    bios_mode_initial = (update_func is None and draw_func is None)
    if bios_mode_initial:
        state.bios_active = True
        # Check auto-boot: is there a boot cart?
        boot = config.boot_cart_path()
        if boot:
            _bios_countdown(boot)
    else:
        state.bios_active = False

    if init_func and not bios_mode_initial:
        init_func()

    running = True
    while running:
        state.keys_prev = state.keys.copy()
        state.mouse_btn_prev = list(state.mouse_btn)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                state.keys[event.key] = True
                if event.key == pygame.K_ESCAPE:
                    if state.editor_mode is not None:
                        state.editor_mode = None
                    else:
                        running = False
                elif event.key == pygame.K_F1:
                    editors.toggle("sprite")
                elif event.key == pygame.K_F2:
                    editors.toggle("map")
                elif event.key == pygame.K_F3:
                    from . import editors_audio
                    editors_audio.toggle("sfx")
                elif event.key == pygame.K_F4:
                    from . import editors_audio
                    editors_audio.toggle("music")
                elif event.key == pygame.K_F6:
                    from . import code_editor
                    code_editor._ensure_state()
                    if state.editor_mode == "code":
                        state.editor_mode = None
                    else:
                        state.editor_mode = "code"
                elif event.key == pygame.K_F7:
                    from . import editor_pdf
                    editor_pdf.toggle()
                elif event.key == pygame.K_F11:
                    toggle_fullscreen()
                elif event.key == pygame.K_F12:
                    # F12 = emergency exit to BIOS, anytime
                    bios.go_to_bios()
                elif event.key == pygame.K_F9 and state.editor_mode != "code":
                    # F9 outside code editor: reload cart code
                    from . import code_editor
                    code_editor._ensure_state()
                    ok, msg = code_editor.execute_code()
                    print(f"[F9] {msg}")
                elif event.key == pygame.K_F5:
                    _save_current_cart(also_pdf=True)
                elif event.key == pygame.K_F8:
                    _load_current_cart()
            elif event.type == pygame.KEYUP:
                state.keys[event.key] = False

        # Mouse state (display -> logic coordinates)
        mx, my = pygame.mouse.get_pos()
        scale = getattr(state, "display_scale", SCALE)
        # Letterbox-Offset: bei fullscreen can das Bild zentriert sein
        offset_x = (getattr(state, "display_w", WIDTH * SCALE) - WIDTH * scale) // 2
        offset_y = (getattr(state, "display_h", HEIGHT * SCALE) - HEIGHT * scale) // 2
        state.mouse_x = max(0, min(WIDTH - 1, (mx - offset_x) // max(1, scale)))
        state.mouse_y = max(0, min(HEIGHT - 1, (my - offset_y) // max(1, scale)))
        buttons = pygame.mouse.get_pressed(num_buttons=3)
        state.mouse_btn = list(buttons)

        # Cart load error takes priority over everything (even BIOS)
        cart_err = getattr(state, "cart_load_error", None)
        if cart_err:
            _draw_cart_load_error(cart_err)
            # Dismissable with ESC or F12
            if state.keys.get(pygame.K_ESCAPE, False) and not state.keys_prev.get(pygame.K_ESCAPE, False):
                state.cart_load_error = None
                bios.go_to_bios()
            elif state.keys.get(pygame.K_F12, False) and not state.keys_prev.get(pygame.K_F12, False):
                state.cart_load_error = None
                bios.go_to_bios()
            elif state.keys.get(pygame.K_F6, False) and not state.keys_prev.get(pygame.K_F6, False):
                state.cart_load_error = None
                state.editor_mode = "code"
        # BIOS takes priority over everything else
        elif bios.is_bios_active():
            bios.bios_update()
            bios.bios_draw()
        elif state.editor_mode == "sprite":
            editors.sprite_editor_update()
            editors.sprite_editor_draw()
        elif state.editor_mode == "map":
            editors.map_editor_update()
            editors.map_editor_draw()
        elif state.editor_mode == "sfx":
            from . import editors_audio
            editors_audio.sfx_editor_update()
            editors_audio.sfx_editor_draw()
        elif state.editor_mode == "music":
            from . import editors_audio
            editors_audio.music_editor_update()
            editors_audio.music_editor_draw()
        elif state.editor_mode == "code":
            from . import code_editor
            code_editor.code_editor_update()
            code_editor.code_editor_draw()
        elif state.editor_mode == "pdf":
            from . import editor_pdf
            editor_pdf.pdf_editor_update()
            editor_pdf.pdf_editor_draw()
        else:
            # Wenn Cart-Code per F9 geload wurde, dessen Funktionen verwenden;
            # otherwise original functions from run()'s caller
            cur_update = getattr(state, "cart_update_fn", None) or update_func
            cur_draw   = getattr(state, "cart_draw_fn", None)   or draw_func
            if cur_update is None or cur_draw is None:
                # Kein Cart loaded, kein BIOS aktiv -> ins BIOS
                state.bios_active = True
                continue
            try:
                cur_update()
                cur_draw()
            except Exception as e:
                # Catch cart code errors instead of crashing the program
                import traceback
                err = traceback.format_exc(limit=2)
                from .graphics import cls as _cls, text as _text
                _cls(0)
                _text("CART RUNTIME ERROR:", 4, 4, 8)
                for li, ln in enumerate(err.splitlines()[-6:]):
                    _text(ln[:60], 4, 16 + li * 8, 6)
                _text("F6 EDITOR  ESC QUIT  F12 BIOS", 4, HEIGHT - 10, 7)

        # Advance tracker each frame
        tracker.tick()

        # Process cart switch requests (run_cart, push_cart, pop_cart)
        from . import cart_runtime
        cart_runtime.process_pending_actions()

        # Skaliertes Bild aufs Display blit - mit Letterbox bei fullscreen
        scale = getattr(state, "display_scale", SCALE)
        scaled = pygame.transform.scale(state.screen,
                                        (WIDTH * scale, HEIGHT * scale))
        surf = pygame.display.get_surface()
        if getattr(state, "fullscreen", False):
            # Black background for letterbox areas
            surf.fill((0, 0, 0))
            offset_x = (state.display_w - WIDTH * scale) // 2
            offset_y = (state.display_h - HEIGHT * scale) // 2
            surf.blit(scaled, (offset_x, offset_y))
        else:
            surf.blit(scaled, (0, 0))
        pygame.display.flip()
        state.clock.tick(FPS)
        state.frame_count += 1

    pygame.quit()
    sys.exit()
