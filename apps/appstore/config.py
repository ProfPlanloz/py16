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
