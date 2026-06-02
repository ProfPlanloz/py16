"""Input-Verarbeitung: uebersetzt Taps in Zustandsaenderungen.

update() ist der vom Host gerufene Einstieg (nur wenn das Fenster im
Vordergrund ist) und verzweigt nach S.view. open_info() kapselt den
Wechsel in die Info-Karte samt Icon-Laden.
"""
import py16
import threading

from .config import FILTERS, ROW_H
from .state import S
from .helpers import visible_items, layout
from .tasks import start_bg, bg_refresh, bg_install, load_item_icon, bg_load_counts


def open_info(item, came_from):
    """Info-Karte fuer ein Item oeffnen und dessen Icon laden."""
    S.info = item
    S.info_from = came_from
    S.info_scroll = 0
    S.view = "info"
    load_item_icon(item)
    # echte Download-Zahlen einmalig nachladen (eigener Thread, non-blocking)
    if not S.counts_loaded and not S.counts_loading:
        threading.Thread(target=bg_load_counts, daemon=True).start()


def _update_info(lx, ly, tap, ww, wh, L):
    # Textspalte scrollen (Pfeile am rechten Rand)
    if tap and ww - 12 <= lx <= ww - 4:
        if ly <= wh // 2:
            S.info_scroll = max(0, S.info_scroll - 1)
        else:
            S.info_scroll += 1  # Obergrenze begrenzt der Renderer
        return
    if tap and L["btn_y"] <= ly <= L["btn_y"] + 10:
        if 6 <= lx <= 56:  # BACK
            S.view = S.info_from
            py16.tone(440, 8, py16.WAVE_SQUARE)
            return
        if ww - 60 <= lx <= ww - 6 and S.info is not None and not S.loading:
            S.pending = S.info
            S.confirm_from = "info"
            S.view = "confirm"
            py16.tone(660, 10, py16.WAVE_SQUARE)
        return


def _update_confirm(lx, ly, tap, ww, wh, L):
    if tap and L["btn_y"] <= ly <= L["btn_y"] + 10:
        if 6 <= lx <= 56:  # CANCEL
            S.view = S.confirm_from
            S.pending = None
            py16.tone(330, 8, py16.WAVE_SQUARE)
            return
        if ww - 60 <= lx <= ww - 6:  # bestaetigtes INSTALL
            if S.pending is not None and not S.loading:
                start_bg(bg_install, S.pending)
                S.view = S.confirm_from
                S.pending = None
                py16.tone(880, 10, py16.WAVE_SQUARE)
            return


def _update_list(lx, ly, m_pressed, m_held, tap, ww, wh, L, vis):
    if not m_held:
        S.drag_thumb = False

    # Kategorie-Auswahl: << / >> blaettern durch FILTERS
    if tap and L["sel_y"] <= ly <= L["sel_y"] + L["sel_h"]:
        aw = L["arrow_w"]
        row_x = 4
        row_w = ww - 8
        idx = next((i for i, (l, v) in enumerate(FILTERS) if v == S.filter), 0)
        step = 0
        if row_x <= lx <= row_x + aw:                       # <<
            step = -1
        elif row_x + row_w - aw <= lx <= row_x + row_w:     # >>
            step = 1
        if step:
            idx = (idx + step) % len(FILTERS)
            S.filter = FILTERS[idx][1]
            S.selected = -1
            S.scroll = 0
            py16.tone(700, 6, py16.WAVE_SQUARE)
        return

    # REFRESH / INFO / INSTALL Buttons
    if tap and L["btn_y"] <= ly <= L["btn_y"] + 10:
        bw = L["btn_w"]
        if L["btn1_x"] <= lx <= L["btn1_x"] + bw:          # REFRESH
            start_bg(bg_refresh)
            py16.tone(440, 10, py16.WAVE_SQUARE)
            return
        if L["btn2_x"] <= lx <= L["btn2_x"] + bw:          # INFO
            if 0 <= S.selected < len(vis):
                open_info(vis[S.selected], "list")
                py16.tone(770, 10, py16.WAVE_SQUARE)
            return
        if L["btn3_x"] <= lx <= L["btn3_x"] + bw:          # INSTALL
            if 0 <= S.selected < len(vis):
                S.pending = vis[S.selected]
                S.confirm_from = "list"
                S.view = "confirm"
                py16.tone(660, 10, py16.WAVE_SQUARE)
            return

    list_y, list_h = L["list_y"], L["list_h"]
    sb_x = L["sb_x"]
    vr = L["visible_rows"]
    n = len(vis)
    max_scroll = max(0, n - vr)
    track_top = list_y + 8
    track_h = max(1, list_h - 16)

    # Scrollbar-Bereich
    if sb_x <= lx <= sb_x + 8 and list_y <= ly <= list_y + list_h:
        if ly <= list_y + 8:                       # Pfeil hoch
            if m_pressed:
                S.scroll = max(0, S.scroll - 1)
                S.hold_t = 0
            elif m_held:
                S.hold_t += 1
                if S.hold_t > 12 and S.hold_t % 3 == 0:
                    S.scroll = max(0, S.scroll - 1)
            return
        if ly >= list_y + list_h - 8:               # Pfeil runter
            if m_pressed:
                S.scroll = min(max_scroll, S.scroll + 1)
                S.hold_t = 0
            elif m_held:
                S.hold_t += 1
                if S.hold_t > 12 and S.hold_t % 3 == 0:
                    S.scroll = min(max_scroll, S.scroll + 1)
            return
        if m_pressed:                               # Thumb-Bereich -> Ziehen starten
            S.drag_thumb = True

    # Thumb scrubben (laeuft weiter, auch wenn der Zeiger den Streifen verlaesst)
    if S.drag_thumb and m_held and max_scroll > 0:
        thumb_h = max(6, track_h * vr // max(1, n))
        denom = max(1, track_h - thumb_h)
        s = (ly - track_top - thumb_h // 2) * max_scroll // denom
        S.scroll = min(max_scroll, max(0, s))
        return

    # Listenzeilen: 1. Tap markiert, 2. Tap auf gleiche Zeile oeffnet die Info-Karte
    if tap and 6 <= lx <= sb_x - 2 and list_y <= ly <= list_y + list_h:
        idx = S.scroll + (ly - list_y) // ROW_H
        if 0 <= idx < n:
            if idx == S.selected:
                open_info(vis[idx], "list")
                py16.tone(990, 8, py16.WAVE_SQUARE)
            else:
                S.selected = idx
                py16.tone(880, 8, py16.WAVE_SQUARE)
        return


def update(win, lx, ly, m_pressed, m_sec_pressed, m_held):
    """Vom Host gerufen, solange das Fenster im Vordergrund ist."""
    ww, wh = win["w"], win["h"]
    L = layout(ww, wh)
    vis = visible_items()
    tap = m_pressed or m_sec_pressed

    if S.view == "info":
        _update_info(lx, ly, tap, ww, wh, L)
        return
    if S.view == "confirm":
        _update_confirm(lx, ly, tap, ww, wh, L)
        return
    _update_list(lx, ly, m_pressed, m_held, tap, ww, wh, L, vis)


def init(win):
    """Einmaliger Start: Index laden, falls noch leer."""
    if not S.items and not S.loading:
        start_bg(bg_refresh)
