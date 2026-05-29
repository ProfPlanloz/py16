# App-Store fuer PY16OS — laedt Apps + Icons aus einem GitHub-Repo nach apps/.
#
# REPO-LAYOUT auf GitHub:
#   <repo>/
#     index.json
#     apps/<id>/<id>.py            -> Plugin-Code
#     apps/<id>/<id>.p16img        -> Plugin-Icon
#     carts/<name>.pdf             -> Spiel-Carts (.pdf / .p16)
#     py16img/<name>.p16img        -> Standalone-Icon-Sammlung
#
# INDEX.JSON-FORMAT:
# {
#   "apps": [
#     {"id":"ticker","name":"TICKER","desc":"DEMO","version":"1.0",
#      "files":["apps/ticker/ticker.py","apps/ticker/ticker.p16img"]}
#   ]
# }
#
# NACH DEM INSTALL:
#   In CMD "RELOAD" eingeben (oder Cart neu starten).
#   load_plugins() registriert neue .py-Plugins und legt beim Erstkontakt
#   automatisch ein Desktop-Icon an (siehe known_plugins).
#
# UI-BEDIENUNG:
#   - Oben Tabs ALL / APP / CART / IMG filtern die Liste nach Typ.
#   - Ein Tap markiert einen Eintrag, ein zweiter Tap oeffnet die DETAIL-Ansicht
#     (volle Beschreibung, Version, Dateiliste). BACK fuehrt zurueck.
#   - Scrollbar: Pfeile gedrueckt halten = Dauerscroll; Mittelbereich ziehen
#     = Thumb scrubben.
#
# === KONFIGURATION ===
import py16
import os
import json
import threading
import urllib.request

REPO_BASE = "https://raw.githubusercontent.com/ProfPlanloz/py16_appstore/main"
INDEX_PATH = "index.json"

# Routing-Tabelle: (Pfad-Praefix im Repo, Endung)  ->  lokales Zielverzeichnis.
# Reihenfolge zaehlt; die erste passende Regel gewinnt.
# Leerer String "" = matched immer (Fallback / Catch-all).
# Neuer Dateityp? Einfach hier eine Zeile zufuegen.
ROUTING_RULES = [
    # standalone Icon-Sammlung bleibt in py16img/
    {"prefix": "py16img/",  "ext": ".p16img", "dest": "py16img"},
    # Plugin-Code und Plugin-Icons gehoeren in apps/
    {"prefix": "",          "ext": ".py",     "dest": "apps"},
    {"prefix": "apps/",     "ext": ".p16img", "dest": "apps"},
    # Carts liegen im Root, von FILES aus startbar
    {"prefix": "",          "ext": ".pdf",    "dest": "."},
    {"prefix": "",          "ext": ".p16",    "dest": "."},
    # weitere Beispiele (auskommentiert):
    # {"prefix": "",        "ext": ".txt",    "dest": "notes"},
    # {"prefix": "",        "ext": ".wav",    "dest": "audio"},
    # {"prefix": "",        "ext": ".ogg",    "dest": "audio"},
    # {"prefix": "",        "ext": ".mp3",    "dest": "audio"},
    # {"prefix": "lang/",   "ext": ".json",   "dest": "lang"},
]
FALLBACK_DEST = "."  # alles, was keine Regel matched

APP = {
    "id": "appstore",
    "name": "STORE",
    "w": 180,
    "h": 150,
    "resizable": True,
    "min_w": 140,
    "min_h": 100,
}

# Filter-Tabs: (Label, kind)  -  kind=None heisst "alles".
_FILTERS = [("ALL", None), ("APP", "app"), ("CART", "cart"), ("IMG", "icon")]

# Hoehe einer Listenzeile (Name + Beschreibung uebereinander, mit Luft dazwischen).
_ROW_H = 13

# --- State (Modul-Ebene) ---
_items = []
_status = "TAP REFRESH"
_loading = False
_selected = -1
_scroll = 0
_filter = None        # None | "app" | "cart" | "icon"
_view = "list"        # "list" | "info" | "confirm"
_info = None          # Item-Dict der Info-Karte
_info_from = "list"   # Ansicht, zu der BACK aus der Info zurueckkehrt
_info_scroll = 0      # vertikaler Scroll der Info-Textspalte
_pending = None       # Item, das auf Install-Bestaetigung wartet
_confirm_from = "list"  # Ansicht, zu der CANCEL zurueckkehrt
_icon_cache = None    # Icon des Info-Items: (w, h, grid) oder None
_icon_err = ""        # Fehlertext, falls Icon-Laden scheitert
_icon_loading = False  # Icon wird gerade aus dem Repo nachgeladen
_icon_repo_cache = {}  # ref -> (w,h,grid) | Fehlertext (schon geholte Repo-Icons)
_icon_token = 0       # schuetzt vor verspaeteten Hintergrund-Fetches
_hold_t = 0           # Frame-Zaehler fuer Pfeil-Dauerscroll
_drag_thumb = False   # gerade am Scroll-Thumb ziehen?


def _set_status(msg):
    global _status
    _status = str(msg)[:34]


def _fetch_text(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8")


def _fetch_bytes(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read()


def _dest_for(rel_path):
    """Pfad im Repo -> lokales Ziel anhand ROUTING_RULES."""
    rel_low = rel_path.lower().lstrip("/")
    base = os.path.basename(rel_path)
    for rule in ROUTING_RULES:
        if rel_low.startswith(rule["prefix"].lower()) and rel_low.endswith(rule["ext"].lower()):
            return os.path.join(rule["dest"], base) if rule["dest"] != "." else base
    return base if FALLBACK_DEST == "." else os.path.join(FALLBACK_DEST, base)


# === UX-Helfer ===

def _item_kind(item):
    """Typ eines Eintrags aus den Datei-Endungen ableiten."""
    exts = [os.path.splitext(f)[1].lower() for f in item.get("files", [])]
    if ".py" in exts:
        return "app"
    if ".pdf" in exts or ".p16" in exts:
        return "cart"
    if ".p16img" in exts:
        return "icon"
    return "other"


def _visible_items():
    """Liste gefiltert nach aktivem Tab."""
    if _filter is None:
        return _items
    return [it for it in _items if _item_kind(it) == _filter]


def _wrap(s, width):
    """Wortweiser Umbruch auf width Zeichen; lange Tokens werden hart gebrochen."""
    width = max(1, width)
    out = []
    cur = ""
    for word in str(s).split():
        while len(word) > width:
            if cur:
                out.append(cur)
                cur = ""
            out.append(word[:width])
            word = word[width:]
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= width:
            cur += " " + word
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


def _hexval(c):
    """Ein Zeichen -> Palettenindex 0..15. Ungueltiges -> 7 (transparent)."""
    try:
        v = int(c, 16)
        return v if 0 <= v <= 15 else 7
    except Exception:
        return 7


def _parse_p16img(text):
    """Text einer .p16img-Datei -> (w, h, grid[y][x]=index) oder None."""
    w = h = 0
    rows = []
    for raw in text.split("\n"):
        s = raw.rstrip("\r")
        if not s:
            continue
        if s.lstrip().startswith("#"):
            for tok in s.lower().replace("x", " ").split():
                if tok.isdigit():
                    if w == 0:
                        w = int(tok)
                    elif h == 0:
                        h = int(tok)
            continue
        rows.append(s)
    if not rows:
        return None
    if w == 0:
        w = max(len(r) for r in rows)
    if h == 0:
        h = len(rows)
    grid = []
    for y in range(h):
        r = rows[y] if y < len(rows) else ""
        grid.append([_hexval(r[x]) if x < len(r) else 7 for x in range(w)])
    return (w, h, grid)


def _item_icon_ref(item):
    """Repo-relativer Pfad des ersten .p16img eines Eintrags, sonst None."""
    for f in item.get("files", []):
        if str(f).lower().endswith(".p16img"):
            return str(f).lstrip("/")
    return None


def _is_installed(item):
    """Heuristik: gilt als installiert, wenn alle Zieldateien lokal existieren."""
    files = item.get("files", [])
    if not files:
        return False
    return all(os.path.isfile(_dest_for(f)) for f in files)


def _bg_load_icon(token, ref):
    """Repo-Icon nachladen + parsen; cachen und uebernehmen, falls noch aktuell."""
    global _icon_cache, _icon_err, _icon_loading
    try:
        parsed = _parse_p16img(_fetch_text(REPO_BASE + "/" + ref))
        _icon_repo_cache[ref] = parsed if parsed is not None else "BAD FORMAT"
    except Exception as e:
        _icon_repo_cache[ref] = "NET: " + str(e)[:18]
    # nur uebernehmen, wenn die Info-Karte noch dasselbe Item zeigt
    if _view == "info" and _icon_token == token:
        val = _icon_repo_cache.get(ref)
        if isinstance(val, tuple):
            _icon_cache, _icon_err = val, ""
        else:
            _icon_cache, _icon_err = None, str(val)[:24]
        _icon_loading = False


def _load_item_icon(item):
    """Icon des Items laden: lokal (falls installiert) sofort, sonst aus Repo."""
    global _icon_cache, _icon_err, _icon_loading, _icon_token
    _icon_cache = None
    _icon_err = ""
    _icon_loading = False
    _icon_token += 1
    token = _icon_token
    ref = _item_icon_ref(item)
    if not ref:
        _icon_err = "NO ICON"
        return
    local = _dest_for(ref)
    if os.path.isfile(local):
        try:
            with open(local, "r") as f:
                _icon_cache = _parse_p16img(f.read())
            if _icon_cache is None:
                _icon_err = "BAD FORMAT"
        except Exception as e:
            _icon_err = str(e)[:24]
        return
    cached = _icon_repo_cache.get(ref)
    if isinstance(cached, tuple):
        _icon_cache = cached
        return
    if isinstance(cached, str):
        _icon_err = cached[:24]
        return
    _icon_loading = True
    threading.Thread(target=_bg_load_icon, args=(token, ref), daemon=True).start()



def _layout(ww, wh):
    """Alle Layout-Offsets relativ zur Fenster-Ecke (wx, wy)."""
    btn_y = wh - 24
    list_y = 32
    list_h = max(12, btn_y - 4 - list_y)
    sb_x = ww - 12
    # Drei gleich breite Buttons fuer die Listenansicht (REFRESH | INFO | INSTALL)
    bw = max(28, (ww - 16) // 3)
    return {
        "tab_y": 14,
        "tab_h": 9,
        "tab_w": max(1, (ww - 8) // len(_FILTERS)),
        "n_tabs": len(_FILTERS),
        "status_y": 24,
        "list_y": list_y,
        "list_h": list_h,
        "list_w": sb_x - 6,
        "sb_x": sb_x,
        "btn_y": btn_y,
        "foot_y": wh - 12,
        "visible_rows": max(1, list_h // _ROW_H),
        "btn_w": bw,
        "btn1_x": 6,
        "btn2_x": 6 + bw + 2,
        "btn3_x": ww - 6 - bw,
    }


# === Hintergrund-Tasks ===

def _bg_refresh():
    global _items, _loading, _selected, _scroll, _view, _pending
    _loading = True
    # UI sofort in einen sauberen Zustand bringen
    _selected = -1
    _scroll = 0
    _view = "list"
    _pending = None
    _set_status("LOADING INDEX...")
    try:
        data = json.loads(_fetch_text(REPO_BASE + "/" + INDEX_PATH))
        _items = data.get("apps", []) if isinstance(data, dict) else []
        _set_status(str(len(_items)) + " APPS FOUND")
    except Exception as e:
        _items = []
        _set_status("ERR: " + str(e)[:26])
    _loading = False


def _bg_install(item):
    global _loading
    _loading = True
    try:
        files = item.get("files", [])
        if not files:
            _set_status("NO FILES")
            _loading = False
            return
        for i, rel in enumerate(files, 1):
            short = os.path.basename(rel)[:14]
            _set_status("[" + str(i) + "/" + str(len(files)) + "] " + short)
            data = _fetch_bytes(REPO_BASE + "/" + rel.lstrip("/"))
            dest = _dest_for(rel)
            d = os.path.dirname(dest)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
        _set_status("OK - TYPE RELOAD IN CMD")
        # frisch installiertes Icon liegt jetzt lokal -> Repo-Cache dafuer verwerfen
        ref = _item_icon_ref(item)
        if ref:
            _icon_repo_cache.pop(ref, None)
        py16.tone(880, 30, py16.WAVE_SQUARE)
    except Exception as e:
        _set_status("FAIL: " + str(e)[:24])
        py16.tone(200, 30, py16.WAVE_SAW)
    _loading = False


def _start_bg(target, *args):
    if _loading:
        return
    threading.Thread(target=target, args=args, daemon=True).start()


def init(win):
    if not _items and not _loading:
        _start_bg(_bg_refresh)


# === Input ===

def update(win, lx, ly, m_pressed, m_sec_pressed, m_held):
    global _selected, _scroll, _filter, _view, _info, _hold_t, _drag_thumb
    global _pending, _confirm_from, _info_from, _info_scroll

    ww, wh = win["w"], win["h"]
    L = _layout(ww, wh)
    vis = _visible_items()
    tap = m_pressed or m_sec_pressed

    # --- INFO-KARTE ---
    if _view == "info":
        # Textspalte scrollen (Pfeile am rechten Rand)
        if tap and ww - 12 <= lx <= ww - 4:
            if ly <= wh // 2:
                _info_scroll = max(0, _info_scroll - 1)
            else:
                _info_scroll += 1  # Obergrenze begrenzt der Renderer
            return
        if tap and L["btn_y"] <= ly <= L["btn_y"] + 10:
            if 6 <= lx <= 56:  # BACK
                _view = _info_from
                py16.tone(440, 8, py16.WAVE_SQUARE)
                return
            if ww - 60 <= lx <= ww - 6 and _info is not None and not _loading:
                _pending = _info
                _confirm_from = "info"
                _view = "confirm"
                py16.tone(660, 10, py16.WAVE_SQUARE)
            return
        return

    # --- BESTAETIGUNGS-DIALOG ---
    if _view == "confirm":
        if tap and L["btn_y"] <= ly <= L["btn_y"] + 10:
            if 6 <= lx <= 56:  # CANCEL
                _view = _confirm_from
                _pending = None
                py16.tone(330, 8, py16.WAVE_SQUARE)
                return
            if ww - 60 <= lx <= ww - 6:  # bestaetigtes INSTALL
                if _pending is not None and not _loading:
                    _start_bg(_bg_install, _pending)
                    _view = _confirm_from
                    _pending = None
                    py16.tone(880, 10, py16.WAVE_SQUARE)
                return
        return

    # --- LISTEN-ANSICHT ---
    if not m_held:
        _drag_thumb = False

    # Filter-Tabs
    if tap and L["tab_y"] <= ly <= L["tab_y"] + L["tab_h"]:
        ti = (lx - 4) // L["tab_w"]
        if 0 <= ti < L["n_tabs"]:
            new_filter = _FILTERS[ti][1]
            if new_filter != _filter:
                _filter = new_filter
                _selected = -1
                _scroll = 0
            py16.tone(700, 6, py16.WAVE_SQUARE)
        return

    # REFRESH / INFO / INSTALL Buttons
    if tap and L["btn_y"] <= ly <= L["btn_y"] + 10:
        bw = L["btn_w"]
        if L["btn1_x"] <= lx <= L["btn1_x"] + bw:          # REFRESH
            _start_bg(_bg_refresh)
            py16.tone(440, 10, py16.WAVE_SQUARE)
            return
        if L["btn2_x"] <= lx <= L["btn2_x"] + bw:          # INFO
            if 0 <= _selected < len(vis):
                _open_info(vis[_selected], "list")
                py16.tone(770, 10, py16.WAVE_SQUARE)
            return
        if L["btn3_x"] <= lx <= L["btn3_x"] + bw:          # INSTALL
            if 0 <= _selected < len(vis):
                _pending = vis[_selected]
                _confirm_from = "list"
                _view = "confirm"
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
                _scroll = max(0, _scroll - 1)
                _hold_t = 0
            elif m_held:
                _hold_t += 1
                if _hold_t > 12 and _hold_t % 3 == 0:
                    _scroll = max(0, _scroll - 1)
            return
        if ly >= list_y + list_h - 8:               # Pfeil runter
            if m_pressed:
                _scroll = min(max_scroll, _scroll + 1)
                _hold_t = 0
            elif m_held:
                _hold_t += 1
                if _hold_t > 12 and _hold_t % 3 == 0:
                    _scroll = min(max_scroll, _scroll + 1)
            return
        if m_pressed:                               # Thumb-Bereich -> Ziehen starten
            _drag_thumb = True

    # Thumb scrubben (laeuft weiter, auch wenn der Zeiger den Streifen verlaesst)
    if _drag_thumb and m_held and max_scroll > 0:
        thumb_h = max(6, track_h * vr // max(1, n))
        denom = max(1, track_h - thumb_h)
        s = (ly - track_top - thumb_h // 2) * max_scroll // denom
        _scroll = min(max_scroll, max(0, s))
        return

    # Listenzeilen: 1. Tap markiert, 2. Tap auf gleiche Zeile oeffnet die Info-Karte
    if tap and 6 <= lx <= sb_x - 2 and list_y <= ly <= list_y + list_h:
        idx = _scroll + (ly - list_y) // _ROW_H
        if 0 <= idx < n:
            if idx == _selected:
                _open_info(vis[idx], "list")
                py16.tone(990, 8, py16.WAVE_SQUARE)
            else:
                _selected = idx
                py16.tone(880, 8, py16.WAVE_SQUARE)
        return


def _open_info(item, came_from):
    """Info-Karte fuer ein Item oeffnen und dessen Icon laden."""
    global _view, _info, _info_from, _info_scroll
    _info = item
    _info_from = came_from
    _info_scroll = 0
    _view = "info"
    _load_item_icon(item)


# === Rendering ===

def _draw_btn(wx, btn_y, x, w, label, enabled=True):
    """Einheitlicher Button mit zentriertem Label."""
    py16.rectfill(wx + x, btn_y, w, 10, 5 if enabled else 6)
    py16.rect(wx + x, btn_y, w, 10, 0)
    tx = wx + x + max(2, (w - len(label) * 4) // 2)
    py16.text(label, tx, btn_y + 2, 7 if enabled else 5)


def _blit_icon(ox, oy, scale, img):
    """Icon-Grid an (ox,oy) mit ganzzahligem Zoom zeichnen (7 = transparent)."""
    iw, ih, grid = img
    for y in range(ih):
        row = grid[y]
        x = 0
        while x < iw:
            c = row[x]
            x2 = x
            while x2 < iw and row[x2] == c:
                x2 += 1
            if c != 7:
                py16.rectfill(ox + x * scale, oy + y * scale, (x2 - x) * scale, scale, c)
            x = x2


def _draw_confirm(wx, wy, ww, wh, L):
    it = _pending
    files = it.get("files", [])
    dests = [_dest_for(f) for f in files]
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
    can = not _loading
    py16.rectfill(inst_x, btn_y, 54, 10, 5 if can else 6)
    py16.rect(inst_x, btn_y, 54, 10, 0)
    py16.text("INSTALL", inst_x + 10, btn_y + 2, 7 if can else 5)


def _info_lines(it, cw):
    """Metadaten + Beschreibung als Liste von (text, farbe)-Zeilen."""
    lines = []

    def field(label, value):
        if value in (None, "", [], "?"):
            return
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        for j, ln in enumerate(_wrap(str(label) + ": " + str(value), cw)):
            lines.append((ln, 1 if j == 0 else 6))

    field("BY", it.get("author"))
    field("DATE", it.get("created"))
    field("LICENSE", it.get("license"))
    field("LANG", it.get("lang"))
    field("TAGS", it.get("tags"))

    desc = it.get("desc", "")
    if desc:
        lines.append(("", 0))
        for ln in _wrap(desc, cw):
            lines.append((ln, 5))

    files = it.get("files", [])
    if files:
        lines.append(("", 0))
        lines.append(("FILES:", 1))
        for f in files:
            lines.append((str(f)[-cw:], 6))
    return lines


def _draw_info(wx, wy, ww, wh, L):
    global _info_scroll
    it = _info

    # --- Kopf: Icon links, Name/Typ/Version rechts ---
    icon_box = 26
    head_y = wy + 15
    bx, by = wx + 6, head_y
    py16.rect(bx, by, icon_box, icon_box, 6)
    if _icon_cache is not None:
        iw, ih, _g = _icon_cache
        sc = max(1, min((icon_box - 2) // iw, (icon_box - 2) // ih))
        dw, dh = iw * sc, ih * sc
        _blit_icon(bx + (icon_box - dw) // 2, by + (icon_box - dh) // 2, sc, _icon_cache)
    elif _icon_loading:
        py16.text("...", bx + 8, by + 10, 8)
    else:
        py16.text("?", bx + 11, by + 10, 5)

    tx = bx + icon_box + 6
    py16.text(str(it.get("name", "?"))[:12], tx, head_y + 1, 0)
    py16.text((_item_kind(it).upper() + " V" + str(it.get("version", "?")))[:16],
              tx, head_y + 9, 8)
    inst = "INSTALLED" if _is_installed(it) else "NOT INSTALLED"
    py16.text(inst, tx, head_y + 17, 5)

    sep_y = head_y + icon_box + 2
    py16.line(wx + 6, sep_y, wx + ww - 6, sep_y, 6)

    # --- Textspalte: Metadaten + Beschreibung, scrollbar ---
    cw = max(8, (ww - 16) // 4)
    lines = _info_lines(it, cw)
    col_y = sep_y + 3
    bottom = wy + L["btn_y"] - 4
    rows = max(1, (bottom - col_y) // 7)
    max_scroll = max(0, len(lines) - rows)
    if _info_scroll > max_scroll:
        _info_scroll = max_scroll

    py16.clip(wx + 6, col_y, ww - 14, bottom - col_y)
    y = col_y
    for i in range(_info_scroll, min(len(lines), _info_scroll + rows)):
        text, col = lines[i]
        if text:
            py16.text(text, wx + 6, y, col)
        y += 7
    py16.clip()

    # Scroll-Indikatoren, nur wenn noetig
    if max_scroll > 0:
        if _info_scroll > 0:
            py16.text("^", wx + ww - 10, col_y, 0)
        if _info_scroll < max_scroll:
            py16.text("v", wx + ww - 10, bottom - 6, 0)

    btn_y = wy + L["btn_y"]
    _draw_btn(wx, btn_y, 6, 50, "BACK", True)
    inst_x = ww - 60
    _draw_btn(wx, btn_y, inst_x, 54, "INSTALL", not _loading)

    if _loading:
        py16.text(_status, wx + 6, wy + L["foot_y"], 8)


def draw(win, wx, wy, ww, wh, is_active):
    L = _layout(ww, wh)
    vis = _visible_items()

    if _view == "info" and _info is not None:
        _draw_info(wx, wy, ww, wh, L)
        return

    if _view == "confirm" and _pending is not None:
        _draw_confirm(wx, wy, ww, wh, L)
        return

    # Statuszeile
    py16.text(_status, wx + 6, wy + L["status_y"], 1)

    # Filter-Tabs
    ty = wy + L["tab_y"]
    for i, (label, val) in enumerate(_FILTERS):
        tx = wx + 4 + i * L["tab_w"]
        active = (val == _filter)
        py16.rectfill(tx, ty, L["tab_w"] - 1, L["tab_h"], 1 if active else 5)
        py16.rect(tx, ty, L["tab_w"] - 1, L["tab_h"], 0)
        py16.text(label, tx + 3, ty + 2, 7 if active else 0)

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
        thumb_y = track_top + ((track_h - thumb_h) * _scroll // max_scroll if max_scroll else 0)
    py16.rectfill(sb_x + 1, thumb_y, 6, thumb_h, 1)

    # Listenzeilen
    py16.clip(wx + 4, list_y, list_w, list_h)
    for i in range(vr):
        idx = _scroll + i
        if idx >= n:
            break
        item = vis[idx]
        iy = list_y + 2 + i * _ROW_H
        if _selected == idx:
            py16.rectfill(wx + 5, iy - 1, list_w - 2, _ROW_H - 1, 1)
            name_c, desc_c = 7, 6
        else:
            # leichtes Zebra-Muster fuer bessere Lesbarkeit
            if i % 2:
                py16.rectfill(wx + 5, iy - 1, list_w - 2, _ROW_H - 1, 6)
            name_c, desc_c = 0, 1
        py16.text(str(item.get("name", "?"))[:14], wx + 8, iy, name_c)
        py16.text(str(item.get("desc", ""))[:24], wx + 8, iy + 6, desc_c)
    py16.clip()

    # Buttons: REFRESH | INFO | INSTALL
    btn_y = wy + L["btn_y"]
    bw = L["btn_w"]
    _draw_btn(wx, btn_y, L["btn1_x"], bw, "REFRESH", True)
    has_sel = (0 <= _selected < n)
    _draw_btn(wx, btn_y, L["btn2_x"], bw, "INFO", has_sel)
    can_install = has_sel and not _loading
    _draw_btn(wx, btn_y, L["btn3_x"], bw, "INSTALL", can_install)

    # Fusszeile
    foot_y = wy + L["foot_y"]
    if _loading:
        py16.text("WORKING...", wx + 6, foot_y, 8)
    else:
        tag = "" if _filter is None else _filter.upper() + " "
        py16.text(str(n) + " " + tag + "ITEMS", wx + 6, foot_y, 5)
