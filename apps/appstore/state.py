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
