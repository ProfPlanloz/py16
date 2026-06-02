"""Alles Zeichnen: Buttons, Bestaetigungsdialog, Info-Karte, Listenansicht.

draw() ist der vom Host gerufene Einstieg und verteilt nach S.view.
Reines Rendering - keine Zustandsaenderung ausser dem Klemmen von
S.info_scroll an die Listenlaenge.
"""
import py16

from .config import FILTERS, ROW_H
from .state import S
from .helpers import (item_kind, visible_items, is_installed, layout, wrap,
                      blit_icon, dest_for, fmt_count, item_downloads)


def draw_btn(wx, btn_y, x, w, label, enabled=True):
    """Einheitlicher Button mit zentriertem Label."""
    py16.rectfill(wx + x, btn_y, w, 10, 5 if enabled else 6)
    py16.rect(wx + x, btn_y, w, 10, 0)
    tx = wx + x + max(2, (w - len(label) * 4) // 2)
    py16.text(label, tx, btn_y + 2, 7 if enabled else 5)


def draw_confirm(wx, wy, ww, wh, L):
    it = S.pending
    files = it.get("files", [])
    dests = [dest_for(f) for f in files]
    has_code = any(str(f).lower().endswith(".py") for f in files)
    cw = max(8, (ww - 12) // 4)

    py16.text(("INSTALL " + str(it.get("name", "?"))[:12] + "?")[:cw], wx + 6, wy + 16, 0)
    py16.line(wx + 6, wy + 24, wx + ww - 6, wy + 24, 6)

    y = wy + 28
    # Klartext-Warnung: was passiert wirklich?
    if has_code:
        py16.rect(wx + 4, y - 1, ww - 8, 17, 0)
        py16.text("! RUNS AS PYTHON CODE", wx + 8, y, 8)
        py16.text("NO SANDBOX - SEE README", wx + 8, y + 8, 1)
        y += 20
    else:
        py16.text("WRITES " + str(len(files)) + " FILE(S) TO DISK", wx + 8, y, 1)
        y += 9

    py16.text("WRITES TO:", wx + 6, y, 1)
    y += 7

    bottom = wy + L["btn_y"] - 3
    py16.clip(wx + 4, y - 1, ww - 8, max(1, bottom - y))
    if not dests:
        py16.text("(NO FILES)", wx + 8, y, 6)
    for d in dests:
        if y > bottom - 5:
            py16.text("...", wx + 8, y, 6)
            break
        py16.text(("> " + d)[:cw], wx + 8, y, 6)
        y += 7
    py16.clip()

    btn_y = wy + L["btn_y"]
    py16.rectfill(wx + 6, btn_y, 50, 10, 5)
    py16.rect(wx + 6, btn_y, 50, 10, 0)
    py16.text("CANCEL", wx + 12, btn_y + 2, 1)

    inst_x = wx + ww - 60
    can = not S.loading
    py16.rectfill(inst_x, btn_y, 54, 10, 5 if can else 6)
    py16.rect(inst_x, btn_y, 54, 10, 0)
    py16.text("INSTALL", inst_x + 10, btn_y + 2, 7 if can else 5)


def info_lines(it, cw):
    """Metadaten + Beschreibung als Liste von (text, farbe)-Zeilen."""
    lines = []

    def field(label, value):
        if value in (None, "", [], "?"):
            return
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        for j, ln in enumerate(wrap(str(label) + ": " + str(value), cw)):
            lines.append((ln, 1 if j == 0 else 6))

    field("BY", it.get("author"))
    field("DATE", it.get("created"))
    # echte Zahl aus den Releases bevorzugen, sonst statisches index.json-Feld
    live = item_downloads(it)
    dl = live if live is not None else it.get("downloads")
    if dl is not None:
        field("DOWNLOADS", fmt_count(dl))
    field("LICENSE", it.get("license"))
    field("LANG", it.get("lang"))
    field("TAGS", it.get("tags"))

    desc = it.get("desc", "")
    if desc:
        lines.append(("", 0))
        for ln in wrap(desc, cw):
            lines.append((ln, 5))

    files = it.get("files", [])
    if files:
        lines.append(("", 0))
        lines.append(("FILES:", 1))
        for f in files:
            lines.append((str(f)[-cw:], 6))
    return lines


def draw_info(wx, wy, ww, wh, L):
    it = S.info

    # --- Kopf: Icon links, Name/Typ/Version rechts ---
    icon_box = 26
    head_y = wy + 15
    bx, by = wx + 6, head_y
    py16.rect(bx, by, icon_box, icon_box, 6)
    if S.icon_cache is not None:
        iw, ih, _g = S.icon_cache
        sc = max(1, min((icon_box - 2) // iw, (icon_box - 2) // ih))
        dw, dh = iw * sc, ih * sc
        blit_icon(bx + (icon_box - dw) // 2, by + (icon_box - dh) // 2, sc, S.icon_cache)
    elif S.icon_loading:
        py16.text("...", bx + 8, by + 10, 8)
    else:
        py16.text("?", bx + 11, by + 10, 5)

    tx = bx + icon_box + 6
    py16.text(str(it.get("name", "?"))[:12], tx, head_y + 1, 0)
    py16.text((item_kind(it).upper() + " V" + str(it.get("version", "?")))[:16],
              tx, head_y + 9, 8)
    inst = "INSTALLED" if is_installed(it) else "NOT INSTALLED"
    py16.text(inst, tx, head_y + 17, 5)

    sep_y = head_y + icon_box + 2
    py16.line(wx + 6, sep_y, wx + ww - 6, sep_y, 6)

    # --- Textspalte: Metadaten + Beschreibung, scrollbar ---
    cw = max(8, (ww - 16) // 4)
    lines = info_lines(it, cw)
    col_y = sep_y + 3
    bottom = wy + L["btn_y"] - 4
    rows = max(1, (bottom - col_y) // 7)
    max_scroll = max(0, len(lines) - rows)
    if S.info_scroll > max_scroll:
        S.info_scroll = max_scroll

    py16.clip(wx + 6, col_y, ww - 14, bottom - col_y)
    y = col_y
    for i in range(S.info_scroll, min(len(lines), S.info_scroll + rows)):
        text, col = lines[i]
        if text:
            py16.text(text, wx + 6, y, col)
        y += 7
    py16.clip()

    # Scroll-Indikatoren, nur wenn noetig
    if max_scroll > 0:
        if S.info_scroll > 0:
            py16.text("^", wx + ww - 10, col_y, 0)
        if S.info_scroll < max_scroll:
            py16.text("v", wx + ww - 10, bottom - 6, 0)

    btn_y = wy + L["btn_y"]
    draw_btn(wx, btn_y, 6, 50, "BACK", True)
    inst_x = ww - 60
    draw_btn(wx, btn_y, inst_x, 54, "INSTALL", not S.loading)

    if S.loading:
        py16.text(S.status, wx + 6, wy + L["foot_y"], 8)


def draw_list(wx, wy, ww, wh, L, vis):
    # Statuszeile
    py16.text(S.status, wx + 6, wy + L["status_y"], 1)

    # Kategorie-Auswahl:  <<   LABEL   >>
    sy = wy + L["sel_y"]
    sh = L["sel_h"]
    aw = L["arrow_w"]
    row_x = wx + 4
    row_w = ww - 8
    cur_label = next((l for (l, v) in FILTERS if v == S.filter), FILTERS[0][0])

    # linker Pfeil <<
    py16.rectfill(row_x, sy, aw, sh, 5)
    py16.rect(row_x, sy, aw, sh, 0)
    py16.text("<<", row_x + (aw - 8) // 2, sy + 2, 7)
    # rechter Pfeil >>
    rx = row_x + row_w - aw
    py16.rectfill(rx, sy, aw, sh, 5)
    py16.rect(rx, sy, aw, sh, 0)
    py16.text(">>", rx + (aw - 8) // 2, sy + 2, 7)
    # Mitte: aktuelle Auswahl, hervorgehoben
    cx = row_x + aw
    cw = row_w - 2 * aw
    py16.rectfill(cx, sy, cw, sh, 1)
    py16.rect(cx, sy, cw, sh, 0)
    py16.text(cur_label, cx + max(2, (cw - len(cur_label) * 4) // 2), sy + 2, 7)

    list_y = wy + L["list_y"]
    list_h = L["list_h"]
    list_w = L["list_w"]
    sb_x = wx + L["sb_x"]

    py16.rectfill(wx + 4, list_y, list_w, list_h, 7)
    py16.rect(wx + 4, list_y, list_w, list_h, 0)

    # Scrollbar mit Pfeilen
    py16.rectfill(sb_x, list_y, 8, list_h, 6)
    py16.rectfill(sb_x, list_y, 8, 8, 6)
    py16.rect(sb_x, list_y, 8, 8, 0)
    py16.text("^", sb_x + 2, list_y + 1, 0)
    py16.rectfill(sb_x, list_y + list_h - 8, 8, 8, 6)
    py16.rect(sb_x, list_y + list_h - 8, 8, 8, 0)
    py16.text("v", sb_x + 2, list_y + list_h - 7, 0)

    # Scroll-Thumb
    vr = L["visible_rows"]
    n = len(vis)
    track_top = list_y + 8
    track_h = max(1, list_h - 16)
    max_scroll = max(0, n - vr)
    if n <= vr:
        thumb_h, thumb_y = track_h, track_top
    else:
        thumb_h = max(6, track_h * vr // n)
        thumb_y = track_top + ((track_h - thumb_h) * S.scroll // max_scroll if max_scroll else 0)
    py16.rectfill(sb_x + 1, thumb_y, 6, thumb_h, 1)

    # Listenzeilen
    py16.clip(wx + 4, list_y, list_w, list_h)
    for i in range(vr):
        idx = S.scroll + i
        if idx >= n:
            break
        item = vis[idx]
        iy = list_y + 2 + i * ROW_H
        if S.selected == idx:
            py16.rectfill(wx + 5, iy - 1, list_w - 2, ROW_H - 1, 1)
            name_c, desc_c = 7, 6
        else:
            # leichtes Zebra-Muster fuer bessere Lesbarkeit
            if i % 2:
                py16.rectfill(wx + 5, iy - 1, list_w - 2, ROW_H - 1, 6)
            name_c, desc_c = 0, 1
        py16.text(str(item.get("name", "?"))[:14], wx + 8, iy, name_c)
        py16.text(str(item.get("desc", ""))[:24], wx + 8, iy + 6, desc_c)
    py16.clip()

    # Buttons: REFRESH | INFO | INSTALL
    btn_y = wy + L["btn_y"]
    bw = L["btn_w"]
    draw_btn(wx, btn_y, L["btn1_x"], bw, "REFRESH", True)
    has_sel = (0 <= S.selected < n)
    draw_btn(wx, btn_y, L["btn2_x"], bw, "INFO", has_sel)
    can_install = has_sel and not S.loading
    draw_btn(wx, btn_y, L["btn3_x"], bw, "INSTALL", can_install)

    # Fusszeile
    foot_y = wy + L["foot_y"]
    if S.loading:
        py16.text("WORKING...", wx + 6, foot_y, 8)
    else:
        tag = "" if S.filter is None else S.filter.upper() + " "
        py16.text(str(n) + " " + tag + "ITEMS", wx + 6, foot_y, 5)


def draw(win, wx, wy, ww, wh, is_active):
    """Vom Host gerufen, solange das Fenster sichtbar ist."""
    L = layout(ww, wh)
    vis = visible_items()

    if S.view == "info" and S.info is not None:
        draw_info(wx, wy, ww, wh, L)
        return
    if S.view == "confirm" and S.pending is not None:
        draw_confirm(wx, wy, ww, wh, L)
        return
    draw_list(wx, wy, ww, wh, L, vis)
