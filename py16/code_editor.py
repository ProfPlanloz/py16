"""
py16.code_editor
================
F6 code editor. Edits the cart code field or an external
Python-file (`code_file`).

Keys:
  arrows           Move cursor
  Shift+arrows     Auschoose
  Ctrl+A           Alles auschoose
  Ctrl+C/X/V       Copy / Cut / Paste
  Ctrl+Z/Y         Undo / Redo
  Ctrl+F           Suchen
  Ctrl+S           Save external file (if code_file is set)
  Ctrl+L           Externe file neu load
  Tab / Shift+Tab  Einruecken / Ausruecken
  Home / End       Zeilenanfang / -ende
  PgUp / PgDn      Seitenweise scrollen
  F9               Code ausfuehren (Reload)
  ESC              Editor verlassen
"""

import os
import time
import pygame

from . import state
from .core import WIDTH, HEIGHT
from .graphics import cls, rectfill, rect, line, text

# ----------------------------------------------------------------------
# LAYOUT
# ----------------------------------------------------------------------

LINE_H        = 6      # Line height in pixels (5px font + 1px spacing)
GUTTER_W      = 18     # Width for line numbers
TOP_BAR_H     = 9
STATUS_BAR_H  = 17     # 2 Zeilen unten (Status + Hilfe)
MARGIN        = 2

# Sichtbarer Textbereich
def _content_rect():
    """(x, y, w, h) der eigentlichen Textflaeche."""
    x = GUTTER_W
    y = TOP_BAR_H + 2
    w = WIDTH - GUTTER_W - MARGIN
    h = HEIGHT - TOP_BAR_H - STATUS_BAR_H - 4
    return x, y, w, h

def _visible_lines():
    _, _, _, h = _content_rect()
    return h // LINE_H

def _visible_cols():
    _, _, w, _ = _content_rect()
    return w // 4    # Font ist 3 Pixel breit + 1 Pixel Abstand

# ----------------------------------------------------------------------
# STATE INIT
# ----------------------------------------------------------------------

def _ensure_state():
    """Initialisiert Editor-State falls noch nicht vorhanden.
    Pruefe jedes Feld einzeln, damit es robust bleibt auch wenn
    extern Felder manipuliert werden."""
    defaults = {
        "ce_lines":        [""],
        "ce_cur_row":      0,
        "ce_cur_col":      0,
        "ce_sel_anchor":   None,
        "ce_scroll_row":   0,
        "ce_scroll_col":   0,
        "ce_clipboard":    "",
        "ce_undo_stack":   [],
        "ce_redo_stack":   [],
        "ce_search_mode":  False,
        "ce_search_text":  "",
        "ce_status_msg":   "",
        "ce_status_time":  0,
        "ce_status_color": 7,
        "ce_blink_frame":  0,
        "ce_dirty":        False,
        "ce_last_mtime":   0,
        "cart_code":       "",
        "cart_code_file":  None,
    }
    for key, default_val in defaults.items():
        if not hasattr(state, key):
            # fresh list/dict copy per key, so we don't
            # versehentlich shared mutable defaults entstehen
            if isinstance(default_val, list):
                setattr(state, key, list(default_val))
            else:
                setattr(state, key, default_val)

# ----------------------------------------------------------------------
# TEXT-HELFER
# ----------------------------------------------------------------------

def _text_to_lines(s):
    if s == "":
        return [""]
    return s.replace("\r\n", "\n").replace("\r", "\n").split("\n")

def _lines_to_text(lines):
    return "\n".join(lines)

def _clamp_cursor():
    """Cursor in gueltigen Bereich zwingen."""
    state.ce_cur_row = max(0, min(len(state.ce_lines) - 1, state.ce_cur_row))
    state.ce_cur_col = max(0, min(len(state.ce_lines[state.ce_cur_row]),
                                  state.ce_cur_col))

def _set_status(msg, color=7):
    state.ce_status_msg = msg
    state.ce_status_color = color
    state.ce_status_time = state.frame_count

def _push_undo():
    """Snapshot vor einer Aenderung save."""
    snapshot = (list(state.ce_lines), state.ce_cur_row, state.ce_cur_col)
    state.ce_undo_stack.append(snapshot)
    if len(state.ce_undo_stack) > 100:
        state.ce_undo_stack.pop(0)
    state.ce_redo_stack.clear()
    state.ce_dirty = True

def _restore_snapshot(snapshot):
    lines, row, col = snapshot
    state.ce_lines = list(lines)
    state.ce_cur_row = row
    state.ce_cur_col = col
    state.ce_sel_anchor = None
    state.ce_dirty = True

# ----------------------------------------------------------------------
# SELECTION
# ----------------------------------------------------------------------

def _selection_range():
    """Returns ((r1,c1),(r2,c2)) normalisiert, oder None."""
    if state.ce_sel_anchor is None:
        return None
    a_row, a_col = state.ce_sel_anchor
    b_row, b_col = state.ce_cur_row, state.ce_cur_col
    if (a_row, a_col) == (b_row, b_col):
        return None
    if (a_row, a_col) <= (b_row, b_col):
        return (a_row, a_col), (b_row, b_col)
    return (b_row, b_col), (a_row, a_col)

def _selection_text():
    rng = _selection_range()
    if rng is None:
        return ""
    (r1, c1), (r2, c2) = rng
    if r1 == r2:
        return state.ce_lines[r1][c1:c2]
    parts = [state.ce_lines[r1][c1:]]
    parts.extend(state.ce_lines[r1+1:r2])
    parts.append(state.ce_lines[r2][:c2])
    return "\n".join(parts)

def _delete_selection():
    """Entfernt die selection. Return True wenn etwas gedeletes wurde."""
    rng = _selection_range()
    if rng is None:
        return False
    (r1, c1), (r2, c2) = rng
    if r1 == r2:
        state.ce_lines[r1] = state.ce_lines[r1][:c1] + state.ce_lines[r1][c2:]
    else:
        merged = state.ce_lines[r1][:c1] + state.ce_lines[r2][c2:]
        del state.ce_lines[r1:r2+1]
        state.ce_lines.insert(r1, merged)
    state.ce_cur_row, state.ce_cur_col = r1, c1
    state.ce_sel_anchor = None
    return True

def _start_or_keep_selection(shift_pressed):
    """Wird vor Cursor-Bewegungen called, wenn Shift gedrueckt ."""
    if shift_pressed:
        if state.ce_sel_anchor is None:
            state.ce_sel_anchor = (state.ce_cur_row, state.ce_cur_col)
    else:
        state.ce_sel_anchor = None

# ----------------------------------------------------------------------
# CLIPBOARD (System wenn moeglich)
# ----------------------------------------------------------------------

def _clipboard_set(s):
    try:
        pygame.scrap.put(pygame.SCRAP_TEXT, s.encode("utf-8"))
    except Exception:
        pass
    state.ce_clipboard = s

def _clipboard_get():
    try:
        data = pygame.scrap.get(pygame.SCRAP_TEXT)
        if data:
            return data.decode("utf-8", errors="replace").rstrip("\x00")
    except Exception:
        pass
    return state.ce_clipboard

# ----------------------------------------------------------------------
# TEXT EINFUEGEN / LOESCHEN
# ----------------------------------------------------------------------

def _insert_text(s):
    """Text an Cursor einfuegen (can Newlines enthalten)."""
    if not s:
        return
    _push_undo()
    if state.ce_sel_anchor is not None:
        _delete_selection()

    parts = s.split("\n")
    cur_line = state.ce_lines[state.ce_cur_row]
    before = cur_line[:state.ce_cur_col]
    after  = cur_line[state.ce_cur_col:]

    if len(parts) == 1:
        state.ce_lines[state.ce_cur_row] = before + parts[0] + after
        state.ce_cur_col += len(parts[0])
    else:
        state.ce_lines[state.ce_cur_row] = before + parts[0]
        for i, p in enumerate(parts[1:-1], start=1):
            state.ce_lines.insert(state.ce_cur_row + i, p)
        last_line = parts[-1]
        state.ce_lines.insert(state.ce_cur_row + len(parts) - 1,
                              last_line + after)
        state.ce_cur_row += len(parts) - 1
        state.ce_cur_col = len(last_line)

def _backspace():
    if state.ce_sel_anchor is not None:
        _push_undo()
        _delete_selection()
        return
    if state.ce_cur_col == 0 and state.ce_cur_row == 0:
        return
    _push_undo()
    if state.ce_cur_col > 0:
        line = state.ce_lines[state.ce_cur_row]
        state.ce_lines[state.ce_cur_row] = line[:state.ce_cur_col-1] + line[state.ce_cur_col:]
        state.ce_cur_col -= 1
    else:
        # Zeile mit voriger zusammenfuehren
        prev = state.ce_lines[state.ce_cur_row - 1]
        cur = state.ce_lines[state.ce_cur_row]
        new_col = len(prev)
        state.ce_lines[state.ce_cur_row - 1] = prev + cur
        del state.ce_lines[state.ce_cur_row]
        state.ce_cur_row -= 1
        state.ce_cur_col = new_col

def _delete_forward():
    if state.ce_sel_anchor is not None:
        _push_undo()
        _delete_selection()
        return
    cur_line = state.ce_lines[state.ce_cur_row]
    if state.ce_cur_col < len(cur_line):
        _push_undo()
        state.ce_lines[state.ce_cur_row] = cur_line[:state.ce_cur_col] + cur_line[state.ce_cur_col+1:]
    elif state.ce_cur_row < len(state.ce_lines) - 1:
        _push_undo()
        state.ce_lines[state.ce_cur_row] = cur_line + state.ce_lines[state.ce_cur_row + 1]
        del state.ce_lines[state.ce_cur_row + 1]

def _enter_with_indent():
    """Newline einfuegen und Einrueckung der vorigen Zeile uebernehmen."""
    _push_undo()
    if state.ce_sel_anchor is not None:
        _delete_selection()
    cur_line = state.ce_lines[state.ce_cur_row]
    indent = ""
    for c in cur_line:
        if c in " \t":
            indent += c
        else:
            break
    # Nach ":" mehr einruecken
    stripped = cur_line.rstrip()
    if stripped.endswith(":"):
        indent += "    "
    before = cur_line[:state.ce_cur_col]
    after  = cur_line[state.ce_cur_col:]
    state.ce_lines[state.ce_cur_row] = before
    state.ce_lines.insert(state.ce_cur_row + 1, indent + after)
    state.ce_cur_row += 1
    state.ce_cur_col = len(indent)

def _indent_selection(outdent=False):
    """Tab/Shift-Tab auf Selection oder currentr Zeile."""
    _push_undo()
    rng = _selection_range()
    if rng:
        (r1, _), (r2, _) = rng
    else:
        r1 = r2 = state.ce_cur_row
    for r in range(r1, r2 + 1):
        if outdent:
            line = state.ce_lines[r]
            removed = 0
            while removed < 4 and line.startswith(" "):
                line = line[1:]
                removed += 1
            state.ce_lines[r] = line
        else:
            state.ce_lines[r] = "    " + state.ce_lines[r]

# ----------------------------------------------------------------------
# DATEI-IO
# ----------------------------------------------------------------------

def _load_external_if_present():
    """Loads externe file wenn cart_code_file gesets ."""
    path = state.cart_code_file
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        state.ce_lines = _text_to_lines(text)
        state.cart_code = text                  # Sync code into cart state
        state.ce_last_mtime = os.path.getmtime(path)
        state.ce_dirty = False
        _set_status(f"LOADED: {os.path.basename(path)}", 11)
    except Exception as e:
        _set_status(f"LOAD ERROR: {e}", 8)

def _check_external_modified():
    """Checks ob externe file gechanges wurde."""
    path = state.cart_code_file
    if not path or not os.path.exists(path):
        return False
    try:
        mtime = os.path.getmtime(path)
        if mtime > state.ce_last_mtime + 0.5:   # 0.5s Toleranz
            return True
    except Exception:
        pass
    return False

def save_external_file():
    """Writes currentn Code in cart_code_file."""
    path = state.cart_code_file
    if not path:
        # Fallback: in cart_code im Speicher schreiben
        state.cart_code = _lines_to_text(state.ce_lines)
        state.ce_dirty = False
        _set_status("IM CART SAVED", 11)
        return
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_lines_to_text(state.ce_lines))
        state.ce_last_mtime = os.path.getmtime(path)
        state.ce_dirty = False
        _set_status(f"SAVED: {os.path.basename(path)}", 11)
    except Exception as e:
        _set_status(f"SAVE-FEHLER: {e}", 8)

# ----------------------------------------------------------------------
# CODE AUSFUEHREN (F9 Reload)
# ----------------------------------------------------------------------

def execute_code():
    """
    Kompiliert den Code, ruft init() auf, und ersets update/draw/init
    in state. Return (ok, error_message).
    """
    code_text = _lines_to_text(state.ce_lines)
    state.cart_code = code_text

    # Erst syntaktisch check
    try:
        compiled = compile(code_text, state.cart_code_file or "<cart>", "exec")
    except SyntaxError as e:
        return False, f"SYNTAX FEHLER ZEILE {e.lineno}: {e.msg}"

    # Globals for cart code: expose entire py16 API
    import py16
    cart_globals = {
        "__name__": "__cart__",
        "__file__": state.cart_code_file or "<cart>",
        "py16": py16,
    }
    # Auch direkte Funktionen available machen (ohne py16.-Praefix)
    for name in py16.__all__:
        cart_globals[name] = getattr(py16, name)

    try:
        exec(compiled, cart_globals)
    except Exception as e:
        import traceback
        tb = traceback.format_exc(limit=3)
        return False, f"LAUFZEITFEHLER:\n{tb.split(chr(10))[-2]}"

    # update/draw/init aus Cart extrahieren
    update_fn = cart_globals.get("update")
    draw_fn   = cart_globals.get("draw")
    init_fn   = cart_globals.get("init")

    if not callable(update_fn) or not callable(draw_fn):
        return False, "CART BRAUCHT update() UND draw() FUNKTIONEN"

    state.cart_update_fn = update_fn
    state.cart_draw_fn = draw_fn
    state.cart_init_fn = init_fn

    if init_fn is not None:
        try:
            init_fn()
        except Exception as e:
            import traceback
            tb = traceback.format_exc(limit=3)
            return False, f"INIT-FEHLER:\n{tb.split(chr(10))[-2]}"

    return True, "RELOAD OK"

# ----------------------------------------------------------------------
# UPDATE (Tastatur-Behandlung)
# ----------------------------------------------------------------------

def _ctrl():  return state.keys.get(pygame.K_LCTRL, False) or state.keys.get(pygame.K_RCTRL, False)
def _shift(): return state.keys.get(pygame.K_LSHIFT, False) or state.keys.get(pygame.K_RSHIFT, False)

def code_editor_update():
    _ensure_state()

    # Externe file - wenn extern gechanges, neu load (sanft)
    if _check_external_modified():
        _load_external_if_present()

    # Search-Mode hat eigene input
    if state.ce_search_mode:
        _search_input()
        return

    # Spezial-keyskombinationen mit Ctrl
    if _ctrl():
        for ev in state.keys:
            if not state.keys.get(ev, False) or state.keys_prev.get(ev, False):
                continue
            if ev == pygame.K_a:
                # Alles selektieren
                state.ce_sel_anchor = (0, 0)
                state.ce_cur_row = len(state.ce_lines) - 1
                state.ce_cur_col = len(state.ce_lines[state.ce_cur_row])
                return
            elif ev == pygame.K_c:
                _clipboard_set(_selection_text())
                _set_status("KOPIERT", 11)
                return
            elif ev == pygame.K_x:
                if state.ce_sel_anchor:
                    _clipboard_set(_selection_text())
                    _push_undo()
                    _delete_selection()
                    _set_status("AUSGESCHNITTEN", 11)
                return
            elif ev == pygame.K_v:
                _insert_text(_clipboard_get())
                _set_status("EINGEFUEGT", 11)
                return
            elif ev == pygame.K_z:
                if state.ce_undo_stack:
                    cur = (list(state.ce_lines), state.ce_cur_row, state.ce_cur_col)
                    state.ce_redo_stack.append(cur)
                    _restore_snapshot(state.ce_undo_stack.pop())
                    _set_status("UNDO", 6)
                return
            elif ev == pygame.K_y:
                if state.ce_redo_stack:
                    cur = (list(state.ce_lines), state.ce_cur_row, state.ce_cur_col)
                    state.ce_undo_stack.append(cur)
                    _restore_snapshot(state.ce_redo_stack.pop())
                    _set_status("REDO", 6)
                return
            elif ev == pygame.K_s:
                save_external_file()
                return
            elif ev == pygame.K_l:
                _load_external_if_present()
                return
            elif ev == pygame.K_f:
                state.ce_search_mode = True
                state.ce_search_text = ""
                _set_status("SUCHE: ", 7)
                return

    # Normale Cursor-keys und Editing
    for ev in list(state.keys.keys()):
        if not state.keys.get(ev, False) or state.keys_prev.get(ev, False):
            continue

        if ev == pygame.K_LEFT:
            _start_or_keep_selection(_shift())
            if state.ce_cur_col > 0:
                state.ce_cur_col -= 1
            elif state.ce_cur_row > 0:
                state.ce_cur_row -= 1
                state.ce_cur_col = len(state.ce_lines[state.ce_cur_row])
        elif ev == pygame.K_RIGHT:
            _start_or_keep_selection(_shift())
            cur_line = state.ce_lines[state.ce_cur_row]
            if state.ce_cur_col < len(cur_line):
                state.ce_cur_col += 1
            elif state.ce_cur_row < len(state.ce_lines) - 1:
                state.ce_cur_row += 1
                state.ce_cur_col = 0
        elif ev == pygame.K_UP:
            _start_or_keep_selection(_shift())
            if state.ce_cur_row > 0:
                state.ce_cur_row -= 1
                state.ce_cur_col = min(state.ce_cur_col, len(state.ce_lines[state.ce_cur_row]))
        elif ev == pygame.K_DOWN:
            _start_or_keep_selection(_shift())
            if state.ce_cur_row < len(state.ce_lines) - 1:
                state.ce_cur_row += 1
                state.ce_cur_col = min(state.ce_cur_col, len(state.ce_lines[state.ce_cur_row]))
        elif ev == pygame.K_HOME:
            _start_or_keep_selection(_shift())
            state.ce_cur_col = 0
        elif ev == pygame.K_END:
            _start_or_keep_selection(_shift())
            state.ce_cur_col = len(state.ce_lines[state.ce_cur_row])
        elif ev == pygame.K_PAGEUP:
            _start_or_keep_selection(_shift())
            state.ce_cur_row = max(0, state.ce_cur_row - _visible_lines())
        elif ev == pygame.K_PAGEDOWN:
            _start_or_keep_selection(_shift())
            state.ce_cur_row = min(len(state.ce_lines) - 1,
                                   state.ce_cur_row + _visible_lines())
        elif ev == pygame.K_BACKSPACE:
            _backspace()
        elif ev == pygame.K_DELETE:
            _delete_forward()
        elif ev == pygame.K_RETURN or ev == pygame.K_KP_ENTER:
            _enter_with_indent()
        elif ev == pygame.K_TAB:
            if _shift():
                _indent_selection(outdent=True)
            else:
                if state.ce_sel_anchor:
                    _indent_selection(outdent=False)
                else:
                    _insert_text("    ")
        elif ev == pygame.K_F9:
            ok, msg = execute_code()
            _set_status(msg, 11 if ok else 8)
        else:
            # Druckbare Zeichen
            ch = _key_to_char(ev)
            if ch:
                _insert_text(ch)

    _clamp_cursor()
    _scroll_to_cursor()

def _key_to_char(key):
    """Konvertiert Pygame-Keycode zu druckbarem Zeichen unter Beruecksichtigung von Shift."""
    shift = _shift()
    # Pygame returns in event.unicode normalerweise das Zeichen, aber wir
    # have only the keycode here. So a manual ASCII table.
    if pygame.K_a <= key <= pygame.K_z:
        ch = chr(key)
        return ch.upper() if shift else ch
    if pygame.K_0 <= key <= pygame.K_9:
        if shift:
            return ")!@#$%^&*("[key - pygame.K_0]
        return chr(key)
    special = {
        pygame.K_SPACE: ' ',
        pygame.K_MINUS: '_' if shift else '-',
        pygame.K_EQUALS: '+' if shift else '=',
        pygame.K_LEFTBRACKET: '{' if shift else '[',
        pygame.K_RIGHTBRACKET: '}' if shift else ']',
        pygame.K_SEMICOLON: ':' if shift else ';',
        pygame.K_QUOTE: '"' if shift else "'",
        pygame.K_COMMA: '<' if shift else ',',
        pygame.K_PERIOD: '>' if shift else '.',
        pygame.K_SLASH: '?' if shift else '/',
        pygame.K_BACKSLASH: '|' if shift else '\\',
        pygame.K_BACKQUOTE: '~' if shift else '`',
    }
    return special.get(key)

def _scroll_to_cursor():
    """Scrolling so anpassen, dass Cursor sichtbar ."""
    vlines = _visible_lines()
    vcols = _visible_cols()

    if state.ce_cur_row < state.ce_scroll_row:
        state.ce_scroll_row = state.ce_cur_row
    elif state.ce_cur_row >= state.ce_scroll_row + vlines:
        state.ce_scroll_row = state.ce_cur_row - vlines + 1

    if state.ce_cur_col < state.ce_scroll_col:
        state.ce_scroll_col = max(0, state.ce_cur_col - 4)
    elif state.ce_cur_col >= state.ce_scroll_col + vcols:
        state.ce_scroll_col = state.ce_cur_col - vcols + 4

# ----------------------------------------------------------------------
# SUCHE
# ----------------------------------------------------------------------

def _search_input():
    """Eigene keysbehandlung im Suche-Modus."""
    for ev in list(state.keys.keys()):
        if not state.keys.get(ev, False) or state.keys_prev.get(ev, False):
            continue
        if ev == pygame.K_ESCAPE:
            state.ce_search_mode = False
            _set_status("", 7)
            return
        elif ev == pygame.K_RETURN:
            _do_search()
            state.ce_search_mode = False
            return
        elif ev == pygame.K_BACKSPACE:
            state.ce_search_text = state.ce_search_text[:-1]
        else:
            ch = _key_to_char(ev)
            if ch:
                state.ce_search_text += ch
    _set_status(f"SUCHE: {state.ce_search_text}", 7)

def _do_search():
    needle = state.ce_search_text
    if not needle:
        return
    needle_lower = needle.lower()
    start_row = state.ce_cur_row
    start_col = state.ce_cur_col + 1
    n = len(state.ce_lines)
    for offset in range(n + 1):
        r = (start_row + offset) % n
        line = state.ce_lines[r].lower()
        col = state.ce_cur_col + 1 if r == start_row and offset == 0 else 0
        if r != start_row or offset > 0:
            col = 0
        if offset == 0:
            col = start_col
        idx = line.find(needle_lower, col)
        if idx >= 0:
            state.ce_cur_row = r
            state.ce_cur_col = idx
            state.ce_sel_anchor = (r, idx + len(needle))
            _scroll_to_cursor()
            _set_status(f"GEFUNDEN ZEILE {r+1}", 11)
            return
    _set_status("NOT FOUND", 8)

# ----------------------------------------------------------------------
# DRAW
# ----------------------------------------------------------------------

def code_editor_draw():
    _ensure_state()
    state.ce_blink_frame += 1

    cls(0)
    cx, cy, cw, ch = _content_rect()

    # Top-Bar
    rectfill(0, 0, WIDTH, TOP_BAR_H, 1)
    title = state.cart_code_file or "[INTERNER CART-CODE]"
    title_short = title if len(title) < 30 else "..." + title[-27:]
    dirty_mark = " *" if state.ce_dirty else ""
    text(f"CODE  {title_short}{dirty_mark}", 2, 2, 7, upper=False)

    # Gutter (Zeilennummern)
    rectfill(0, TOP_BAR_H, GUTTER_W - 1, ch + 2, 1)

    # Sichtbare Zeilen rendern
    vlines = _visible_lines()
    vcols = _visible_cols()
    for i in range(vlines):
        line_idx = state.ce_scroll_row + i
        if line_idx >= len(state.ce_lines):
            break
        y = cy + i * LINE_H

        # Zeilennummer
        text(f"{line_idx+1:3}", 1, y, 6)

        # Selection-Hintergrund
        rng = _selection_range()
        if rng:
            (r1, c1), (r2, c2) = rng
            if r1 <= line_idx <= r2:
                start_col = c1 if line_idx == r1 else 0
                end_col = c2 if line_idx == r2 else len(state.ce_lines[line_idx])
                vis_start = max(start_col - state.ce_scroll_col, 0)
                vis_end = min(end_col - state.ce_scroll_col, vcols)
                if vis_end > vis_start:
                    rectfill(cx + vis_start * 4, y - 1,
                             (vis_end - vis_start) * 4, LINE_H, 13)

        # Zeilentext - upper=False, damit Sonderzeichen wie ()[]{}_=;
        # nicht zu ?-Glyphen werden.
        full_line = state.ce_lines[line_idx]
        visible = full_line[state.ce_scroll_col:state.ce_scroll_col + vcols]
        # Replace tabs with 4 spaces for display
        visible = visible.replace("\t", "    ")
        text(visible, cx, y, 7, upper=False)

    # Cursor (blinken)
    if (state.ce_blink_frame // 30) % 2 == 0 and not state.ce_search_mode:
        cur_screen_row = state.ce_cur_row - state.ce_scroll_row
        cur_screen_col = state.ce_cur_col - state.ce_scroll_col
        if 0 <= cur_screen_row < vlines and 0 <= cur_screen_col <= vcols:
            cx2 = cx + cur_screen_col * 4
            cy2 = cy + cur_screen_row * LINE_H
            line(cx2, cy2 - 1, cx2, cy2 + LINE_H - 2, 7)

    # Status bar
    sy = HEIGHT - STATUS_BAR_H
    rectfill(0, sy, WIDTH, STATUS_BAR_H, 1)
    # Position
    pos_str = f"L{state.ce_cur_row+1:03}:C{state.ce_cur_col+1:03}  LINES:{len(state.ce_lines)}"
    text(pos_str, 2, sy + 1, 6)
    # Statusmeldung (verblasst nach 3 Sekunden)
    if state.ce_status_msg and (state.frame_count - state.ce_status_time) < 180:
        text(state.ce_status_msg, 2, sy + 9, state.ce_status_color)
    else:
        text("F9 RUN  CTRL-S SAVE  CTRL-F FIND  ESC EXIT",
             2, sy + 9, 6)
