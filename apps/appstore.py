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
#     {"id":"ticker","name":"TICKER","desc":"DEMO",
#      "files":["apps/ticker/ticker.py","apps/ticker/ticker.p16img"]}
#   ]
# }
#
# NACH DEM INSTALL:
#   In CMD "RELOAD" eingeben (oder Cart neu starten).
#   load_plugins() registriert neue .py-Plugins und legt beim Erstkontakt
#   automatisch ein Desktop-Icon an (siehe known_plugins).
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

# --- State (Modul-Ebene) ---
_items = []
_status = "TAP REFRESH"
_loading = False
_selected = -1
_scroll = 0


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


def _bg_refresh():
    global _items, _loading
    _loading = True
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


def update(win, lx, ly, m_pressed, m_sec_pressed, m_held):
    global _selected, _scroll
    if not (m_pressed or m_sec_pressed):
        return

    ww, wh = win["w"], win["h"]
    list_y, list_h = 28, wh - 56
    sb_x = ww - 12
    visible_rows = max(1, list_h // 12)
    btn_y = wh - 24

    if btn_y <= ly <= btn_y + 10:
        if 6 <= lx <= 56:
            _start_bg(_bg_refresh)
            py16.tone(440, 10, py16.WAVE_SQUARE)
            return
        if ww - 60 <= lx <= ww - 6:
            if 0 <= _selected < len(_items):
                _start_bg(_bg_install, _items[_selected])
                py16.tone(660, 10, py16.WAVE_SQUARE)
            return

    if sb_x <= lx <= sb_x + 8 and list_y <= ly <= list_y + list_h:
        if ly <= list_y + 8:
            _scroll = max(0, _scroll - 1)
        elif ly >= list_y + list_h - 8:
            max_scroll = max(0, len(_items) - visible_rows)
            _scroll = min(max_scroll, _scroll + 1)
        return

    if 6 <= lx <= sb_x - 2 and list_y <= ly <= list_y + list_h:
        idx = _scroll + (ly - list_y) // 12
        if 0 <= idx < len(_items):
            _selected = idx
            py16.tone(880, 8, py16.WAVE_SQUARE)


def draw(win, wx, wy, ww, wh, is_active):
    py16.text(_status, wx + 6, wy + 16, 1)

    list_y = wy + 28
    list_h = wh - 56
    sb_x = wx + ww - 12
    py16.rectfill(wx + 4, list_y, ww - 18, list_h, 7)
    py16.rect(wx + 4, list_y, ww - 18, list_h, 0)

    py16.rectfill(sb_x, list_y, 8, list_h, 6)
    py16.rectfill(sb_x, list_y, 8, 8, 6)
    py16.rect(sb_x, list_y, 8, 8, 0)
    py16.text("^", sb_x + 2, list_y + 1, 0)
    py16.rectfill(sb_x, list_y + list_h - 8, 8, 8, 6)
    py16.rect(sb_x, list_y + list_h - 8, 8, 8, 0)
    py16.text("v", sb_x + 2, list_y + list_h - 7, 0)

    visible_rows = max(1, list_h // 12)
    py16.clip(wx + 4, list_y, ww - 18, list_h)
    for i in range(visible_rows):
        idx = _scroll + i
        if idx >= len(_items):
            break
        item = _items[idx]
        iy = list_y + 2 + i * 12
        if _selected == idx:
            py16.rectfill(wx + 5, iy - 1, ww - 20, 11, 1)
            name_c, desc_c = 7, 6
        else:
            name_c, desc_c = 1, 5
        py16.text(str(item.get("name", "?"))[:14], wx + 8, iy, name_c)
        py16.text(str(item.get("desc", ""))[:22], wx + 8, iy + 5, desc_c)
    py16.clip()

    btn_y = wy + wh - 24
    py16.rectfill(wx + 6, btn_y, 50, 10, 5)
    py16.rect(wx + 6, btn_y, 50, 10, 0)
    py16.text("REFRESH", wx + 10, btn_y + 2, 7)

    inst_x = wx + ww - 60
    can_install = (0 <= _selected < len(_items)) and not _loading
    py16.rectfill(inst_x, btn_y, 54, 10, 5 if can_install else 6)
    py16.rect(inst_x, btn_y, 54, 10, 0)
    py16.text("INSTALL", inst_x + 10, btn_y + 2, 7 if can_install else 5)

    foot_y = wy + wh - 12
    if _loading:
        py16.text("WORKING...", wx + 6, foot_y, 8)
    else:
        py16.text(str(len(_items)) + " APPS", wx + 6, foot_y, 5)
