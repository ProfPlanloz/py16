# AUTO-GENERATED von build.py - NICHT direkt editieren.
# Quelle: src/appstore/*.py  |  Neu erzeugen: python3 build.py
#
# py16os App-Store (gebuendelte Einzeldatei).


import os
import py16
import json
import threading



# ===== config.py ================================================
"""Statische Konfiguration des App-Stores: Repo, Routing, Fenster, Filter.

Hier liegen ausschliesslich Konstanten - kein veraenderlicher Zustand
(der lebt in state.py) und keine Logik (die liegt in helpers/tasks/views).
"""

# Basis-URL des GitHub-Repos (raw) und Pfad zur Index-Datei darin.
REPO_BASE = "https://raw.githubusercontent.com/ProfPlanloz/py16_appstore/main"
INDEX_PATH = "index.json"


def _derive_releases_api(raw_base):
    """Aus der raw-Basis owner/repo ziehen -> GitHub-Releases-API-URL.

    Liefert "" wenn sich nichts ableiten laesst (dann bleiben die statischen
    downloads-Werte aus index.json die einzige Quelle).
    """
    try:
        tail = raw_base.split("raw.githubusercontent.com/", 1)[1]
        owner, repo = tail.split("/")[:2]
        return "https://api.github.com/repos/" + owner + "/" + repo + "/releases"
    except Exception:
        return ""


# GitHub zaehlt Downloads von Release-Assets automatisch (Feld download_count).
RELEASES_API = _derive_releases_api(REPO_BASE)

# Routing-Tabelle: (Pfad-Praefix im Repo, Endung)  ->  lokales Zielverzeichnis.
# Reihenfolge zaehlt; die erste passende Regel gewinnt.
# Leerer String "" = matched immer (Fallback / Catch-all).
# Neuer Dateityp? Einfach hier eine Zeile zufuegen.
#
# REGEL: Apps (Plugin-Code + zugehoerige Icons) bleiben in apps/, damit der
# Host sie laedt. ALLES ANDERE (Carts, Standalone-Icons, Unbekanntes) landet
# im Ordner downloads/.
ROUTING_RULES = [
    # Plugin-Code und Plugin-Icons gehoeren in apps/ (das sind die "Apps")
    {"prefix": "",          "ext": ".py",     "dest": "apps"},
    {"prefix": "apps/",     "ext": ".p16img", "dest": "apps"},
    # standalone Icon-Sammlung -> downloads/
    {"prefix": "py16img/",  "ext": ".p16img", "dest": "downloads"},
    # Carts -> downloads/
    {"prefix": "",          "ext": ".pdf",    "dest": "downloads"},
    {"prefix": "",          "ext": ".p16",    "dest": "downloads"},
    # Wallpaper / Animationen / Spritesheets -> downloads/
    {"prefix": "",          "ext": ".p16canvas", "dest": "downloads"},
    {"prefix": "",          "ext": ".p16mov",    "dest": "downloads"},
    {"prefix": "",          "ext": ".p16sheet",  "dest": "downloads"},
    # weitere Beispiele (auskommentiert):
    # {"prefix": "",        "ext": ".txt",    "dest": "downloads"},
    # {"prefix": "",        "ext": ".wav",    "dest": "downloads"},
    # {"prefix": "",        "ext": ".ogg",    "dest": "downloads"},
    # {"prefix": "",        "ext": ".mp3",    "dest": "downloads"},
    # {"prefix": "lang/",   "ext": ".json",   "dest": "lang"},
]
FALLBACK_DEST = "downloads"  # alles, was keine Regel matched

# Vom py16os-Host gelesenes Plugin-Manifest.
APP = {
    "id": "appstore",
    "name": "STORE",
    "w": 180,
    "h": 150,
    "resizable": True,
    "min_w": 140,
    "min_h": 100,
}

# Auswahl-Kategorien fuer den <<  LABEL  >>-Umschalter: (Label, kind).
# kind=None heisst "alles". Reihenfolge = Blaetter-Reihenfolge.
FILTERS = [
    ("ALL", None),
    ("APP", "app"),
    ("CART", "cart"),
    ("IMG", "icon"),
    ("CANVAS", "canvas"),
    ("MOV", "movie"),
    ("SHEET", "sheet"),
]

# Hoehe einer Listenzeile (Name + Beschreibung uebereinander, mit Luft dazwischen).
ROW_H = 13

# Typ-Icons fuer Eintraege OHNE eigenes .p16img (item_kind -> Dateiname).
# Diese Dateien liegen lokal (siehe TYPE_ICON_DIRS) und ersetzen den
# Platzhalter ("?") in der Info-Karte.
TYPE_ICONS = {
    "cart":   "pdf.p16img",        # .pdf / .p16
    "canvas": "p16canvas.p16img",  # Wallpaper
    "movie":  "p16mov.p16img",     # Animation
    "sheet":  "p16sheet.p16img",   # Spritesheet
}
# Verzeichnisse, in denen nach den Typ-Icons gesucht wird; erster Treffer gewinnt.
TYPE_ICON_DIRS = ["appstore", "apps/appstore", "apps", "."]

# ===== state.py =================================================
"""Geteilter, veraenderlicher Laufzeit-Zustand.

Alle Module greifen ueber das eine Objekt `S` zu, statt eigene Modul-Globals
zu fuehren. Vorteil: der Zustand liegt an genau einer Stelle, und beim
Buendeln zu einer Datei (build.py) gibt es keine Global-Kollisionen.
"""


class _State:
    def __init__(self):
        self.items = []            # Liste der Katalog-Eintraege (dicts)
        self.status = "TAP REFRESH"  # Statuszeile oben
        self.loading = False       # laeuft gerade ein Hintergrund-Task?
        self.selected = -1         # markierter Listenindex (in der gefilterten Liste)
        self.scroll = 0            # vertikaler Scroll der Liste
        self.filter = None         # None | "app" | "cart" | "icon"
        self.view = "list"         # "list" | "info" | "confirm"
        self.info = None           # Item-Dict der Info-Karte
        self.info_from = "list"    # Ansicht, zu der BACK aus der Info zurueckkehrt
        self.info_scroll = 0       # Scroll der Info-Textspalte
        self.pending = None        # Item, das auf Install-Bestaetigung wartet
        self.confirm_from = "list"  # Ansicht, zu der CANCEL zurueckkehrt
        self.icon_cache = None     # Icon des Info-Items: (w, h, grid) oder None
        self.icon_err = ""         # Fehlertext, falls Icon-Laden scheitert
        self.icon_loading = False  # Icon wird gerade aus dem Repo nachgeladen
        self.icon_repo_cache = {}  # ref -> (w,h,grid) | Fehlertext
        self.icon_token = 0        # schuetzt vor verspaeteten Hintergrund-Fetches
        self.hold_t = 0            # Frame-Zaehler fuer Pfeil-Dauerscroll
        self.drag_thumb = False    # gerade am Scroll-Thumb ziehen?
        # Echte Download-Zahlen aus GitHub-Releases (asset-name -> ...):
        self.dl_counts = {}        # name -> download_count (int)
        self.dl_urls = {}          # name -> browser_download_url (str)
        self.counts_loaded = False  # mind. einmal erfolgreich geladen?
        self.counts_loading = False  # Abruf laeuft gerade?


S = _State()


def set_status(msg):
    """Statuszeile setzen (auf Anzeigebreite gekuerzt)."""
    S.status = str(msg)[:34]

# ===== helpers.py ===============================================
"""Reine Hilfsfunktionen ohne eigenen Zustand (bis auf Lesen aus S).

Routing, Katalog-Abfragen, Textumbruch, .p16img-Parsing/Blitting und das
Layout. Diese Funktionen haben keine Seiteneffekte ausser Zeichnen
(blit_icon) bzw. Lesen von S (visible_items).
"""



# === Routing ===

def dest_for(rel_path):
    """Pfad im Repo -> lokales Ziel anhand ROUTING_RULES."""
    rel_low = rel_path.lower().lstrip("/")
    base = os.path.basename(rel_path)
    for rule in ROUTING_RULES:
        if rel_low.startswith(rule["prefix"].lower()) and rel_low.endswith(rule["ext"].lower()):
            return os.path.join(rule["dest"], base) if rule["dest"] != "." else base
    return base if FALLBACK_DEST == "." else os.path.join(FALLBACK_DEST, base)


# === Katalog-Abfragen ===

def item_kind(item):
    """Typ eines Eintrags aus den Datei-Endungen ableiten."""
    exts = [os.path.splitext(f)[1].lower() for f in item.get("files", [])]
    if ".py" in exts:
        return "app"
    if ".pdf" in exts or ".p16" in exts:
        return "cart"
    if ".p16img" in exts:
        return "icon"
    if ".p16canvas" in exts:
        return "canvas"   # Wallpaper
    if ".p16mov" in exts:
        return "movie"    # Animation
    if ".p16sheet" in exts:
        return "sheet"    # Spritesheet-Animation
    return "other"


def visible_items():
    """Liste gefiltert nach aktivem Tab."""
    if S.filter is None:
        return S.items
    return [it for it in S.items if item_kind(it) == S.filter]


def item_icon_ref(item):
    """Repo-relativer Pfad des ersten .p16img eines Eintrags, sonst None."""
    for f in item.get("files", []):
        if str(f).lower().endswith(".p16img"):
            return str(f).lstrip("/")
    return None


def type_icon_path(kind):
    """Lokalen Pfad zum Typ-Icon fuer ein item_kind finden, sonst None.

    Sucht in TYPE_ICON_DIRS; der erste existierende Treffer gewinnt. Dient
    als Fallback fuer Eintraege ohne eigenes .p16img (Carts, Wallpaper,
    Animationen, Spritesheets).
    """
    name = TYPE_ICONS.get(kind)
    if not name:
        return None
    for d in TYPE_ICON_DIRS:
        p = name if d in ("", ".") else os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


def is_installed(item):
    """Heuristik: gilt als installiert, wenn alle Zieldateien lokal existieren."""
    files = item.get("files", [])
    if not files:
        return False
    return all(os.path.isfile(dest_for(f)) for f in files)


def item_downloads(item):
    """Echte Asset-Download-Zahl (max ueber zugehoerige Assets) oder None.

    Greift auf die aus den GitHub-Releases geladenen Zahlen (S.dl_counts) zu.
    None bedeutet: kein passendes Asset bekannt -> Aufrufer faellt auf das
    statische downloads-Feld zurueck.
    """
    best = None
    for f in item.get("files", []):
        c = S.dl_counts.get(os.path.basename(str(f)))
        if c is not None:
            best = c if best is None else max(best, c)
    return best


# === Text ===

def fmt_count(n):
    """Zahl kompakt darstellen: 999 -> '999', 1234 -> '1.2K', 2_000_000 -> '2.0M'."""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if n < 0:
        return "0"
    if n < 1000:
        return str(n)
    if n < 999500:
        return ("%.1fK" % (n / 1000.0)).replace(".0K", "K")
    return ("%.1fM" % (n / 1000000.0)).replace(".0M", "M")


def wrap(s, width):
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


# === .p16img ===

def hexval(c):
    """Ein Zeichen -> Palettenindex 0..15. Ungueltiges -> 7 (transparent)."""
    try:
        v = int(c, 16)
        return v if 0 <= v <= 15 else 7
    except Exception:
        return 7


def parse_p16img(text):
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
        grid.append([hexval(r[x]) if x < len(r) else 7 for x in range(w)])
    return (w, h, grid)


def blit_icon(ox, oy, scale, img):
    """Icon-Grid an (ox,oy) mit ganzzahligem Zoom zeichnen (7 = transparent).

    Run-Length pro Zeile spart viele rectfill-Aufrufe.
    """
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


# === Layout ===

def layout(ww, wh):
    """Alle Layout-Offsets relativ zur Fenster-Ecke (wx, wy)."""
    btn_y = wh - 24
    list_y = 32
    list_h = max(12, btn_y - 4 - list_y)
    sb_x = ww - 12
    # Drei gleich breite Buttons fuer die Listenansicht (REFRESH | INFO | INSTALL)
    bw = max(28, (ww - 16) // 3)
    return {
        "sel_y": 14,
        "sel_h": 9,
        "arrow_w": 22,
        "status_y": 24,
        "list_y": list_y,
        "list_h": list_h,
        "list_w": sb_x - 6,
        "sb_x": sb_x,
        "btn_y": btn_y,
        "foot_y": wh - 12,
        "visible_rows": max(1, list_h // ROW_H),
        "btn_w": bw,
        "btn1_x": 6,
        "btn2_x": 6 + bw + 2,
        "btn3_x": ww - 6 - bw,
    }

# ===== tasks.py =================================================
"""Netzwerk und Hintergrund-Tasks: Index laden, installieren, Icons holen.

Alle laenger laufenden Aktionen passieren in Threads (start_bg), damit die
60-FPS-Schleife des Hosts nicht blockiert. Ergebnisse landen in S.
"""



# === Netzwerk ===

def fetch_text(url):
    import urllib.request
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8")


def fetch_bytes(url):
    import urllib.request
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read()


# === Hintergrund-Tasks ===

def _populate_counts():
    """Releases-API lesen und S.dl_counts / S.dl_urls fuellen (synchron).

    GitHub verlangt einen User-Agent; ohne kommt 403 zurueck. Fehler werden
    geschluckt - dann bleiben die statischen downloads-Werte massgeblich.
    """
    if not RELEASES_API:
        return
    import urllib.request
    try:
        req = urllib.request.Request(RELEASES_API,
                                     headers={"User-Agent": "py16os-appstore"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return
    counts, urls = {}, {}
    if isinstance(data, list):
        for rel in data:
            for asset in (rel.get("assets") or []):
                name = asset.get("name")
                if not name:
                    continue
                counts[name] = asset.get("download_count", 0)
                if asset.get("browser_download_url"):
                    urls[name] = asset["browser_download_url"]
    S.dl_counts = counts
    S.dl_urls = urls
    S.counts_loaded = True


def bg_load_counts():
    """Counts im Hintergrund laden (eigener Guard, unabhaengig von S.loading)."""
    if S.counts_loading:
        return
    S.counts_loading = True
    try:
        _populate_counts()
    finally:
        S.counts_loading = False


def bg_refresh():
    S.loading = True
    # UI sofort in einen sauberen Zustand bringen
    S.selected = -1
    S.scroll = 0
    S.view = "list"
    S.pending = None
    set_status("LOADING INDEX...")
    try:
        data = json.loads(fetch_text(REPO_BASE + "/" + INDEX_PATH))
        S.items = data.get("apps", []) if isinstance(data, dict) else []
        set_status(str(len(S.items)) + " APPS FOUND")
    except Exception as e:
        S.items = []
        set_status("ERR: " + str(e)[:26])
    # echte Download-Zahlen gleich mitladen (selber Thread, schluckt Fehler)
    _populate_counts()
    S.loading = False


def bg_install(item):
    S.loading = True
    try:
        files = item.get("files", [])
        if not files:
            set_status("NO FILES")
            S.loading = False
            return
        for i, rel in enumerate(files, 1):
            short = os.path.basename(rel)[:14]
            set_status("[" + str(i) + "/" + str(len(files)) + "] " + short)
            # Wenn ein Release-Asset bekannt ist, von dort laden -> GitHub
            # zaehlt den Download. Sonst Fallback auf den raw-Pfad.
            base = os.path.basename(str(rel))
            url = S.dl_urls.get(base) or (REPO_BASE + "/" + rel.lstrip("/"))
            data = fetch_bytes(url)
            dest = dest_for(rel)
            d = os.path.dirname(dest)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
        set_status("OK - TYPE RELOAD IN CMD")
        # frisch installiertes Icon liegt jetzt lokal -> Repo-Cache dafuer verwerfen
        ref = item_icon_ref(item)
        if ref:
            S.icon_repo_cache.pop(ref, None)
        py16.tone(880, 30, py16.WAVE_SQUARE)
    except Exception as e:
        set_status("FAIL: " + str(e)[:24])
        py16.tone(200, 30, py16.WAVE_SAW)
    S.loading = False


def start_bg(target, *args):
    if S.loading:
        return
    threading.Thread(target=target, args=args, daemon=True).start()


# === Icon-Laden fuer die Info-Karte ===

def _load_type_icon(item):
    """Typ-Icon (kind-basiert) lokal laden und in S.icon_cache setzen.

    Rueckgabe True bei Erfolg. Dient als Fallback fuer Eintraege ohne
    eigenes .p16img bzw. wenn das eigene Icon nicht ladbar ist.
    """
    if item is None:
        return False
    path = type_icon_path(item_kind(item))
    if not path:
        return False
    try:
        with open(path, "r") as f:
            img = parse_p16img(f.read())
        if img is not None:
            S.icon_cache = img
            return True
    except Exception:
        pass
    return False


def bg_load_icon(token, ref):
    """Repo-Icon nachladen + parsen; cachen und uebernehmen, falls noch aktuell."""
    try:
        parsed = parse_p16img(fetch_text(REPO_BASE + "/" + ref))
        S.icon_repo_cache[ref] = parsed if parsed is not None else "BAD FORMAT"
    except Exception as e:
        S.icon_repo_cache[ref] = "NET: " + str(e)[:18]
    # nur uebernehmen, wenn die Info-Karte noch dasselbe Item zeigt
    if S.view == "info" and S.icon_token == token:
        val = S.icon_repo_cache.get(ref)
        if isinstance(val, tuple):
            S.icon_cache, S.icon_err = val, ""
        elif _load_type_icon(S.info):
            S.icon_err = ""           # eigenes Icon fehlgeschlagen -> Typ-Icon
        else:
            S.icon_cache, S.icon_err = None, str(val)[:24]
        S.icon_loading = False


def load_item_icon(item):
    """Icon des Items laden: lokal (falls installiert) sofort, sonst aus Repo.

    Hat ein Eintrag kein eigenes .p16img, wird ein Typ-Icon als Fallback
    angezeigt (statt des "?"-Platzhalters).
    """
    S.icon_cache = None
    S.icon_err = ""
    S.icon_loading = False
    S.icon_token += 1
    token = S.icon_token
    ref = item_icon_ref(item)
    if not ref:
        if not _load_type_icon(item):
            S.icon_err = "NO ICON"
        return
    local = dest_for(ref)
    if os.path.isfile(local):
        try:
            with open(local, "r") as f:
                S.icon_cache = parse_p16img(f.read())
            if S.icon_cache is None and not _load_type_icon(item):
                S.icon_err = "BAD FORMAT"
        except Exception as e:
            S.icon_err = str(e)[:24]
        return
    cached = S.icon_repo_cache.get(ref)
    if isinstance(cached, tuple):
        S.icon_cache = cached
        return
    if isinstance(cached, str):
        S.icon_err = cached[:24]
        return
    S.icon_loading = True
    threading.Thread(target=bg_load_icon, args=(token, ref), daemon=True).start()

# ===== views.py =================================================
"""Alles Zeichnen: Buttons, Bestaetigungsdialog, Info-Karte, Listenansicht.

draw() ist der vom Host gerufene Einstieg und verteilt nach S.view.
Reines Rendering - keine Zustandsaenderung ausser dem Klemmen von
S.info_scroll an die Listenlaenge.
"""



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

# ===== controller.py ============================================
"""Input-Verarbeitung: uebersetzt Taps in Zustandsaenderungen.

update() ist der vom Host gerufene Einstieg (nur wenn das Fenster im
Vordergrund ist) und verzweigt nach S.view. open_info() kapselt den
Wechsel in die Info-Karte samt Icon-Laden.
"""



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
