"""Netzwerk und Hintergrund-Tasks: Index laden, installieren, Icons holen.

Alle laenger laufenden Aktionen passieren in Threads (start_bg), damit die
60-FPS-Schleife des Hosts nicht blockiert. Ergebnisse landen in S.
"""
import os
import json
import threading
import py16

from .config import REPO_BASE, INDEX_PATH, RELEASES_API
from .state import S, set_status
from .helpers import parse_p16img, dest_for, item_icon_ref, item_kind, type_icon_path


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
