"""py16os App-Store - modulare Fassung.

Der py16os-Host erwartet auf Modulebene: APP (dict) sowie die Funktionen
init / update / draw. Dieses Paket reicht sie aus den Untermodulen durch:

    config.py      - Konstanten (Repo, Routing, APP, Filter)
    state.py       - geteilter Laufzeit-Zustand S
    helpers.py     - reine Hilfsfunktionen (Routing, Text, p16img, Layout)
    tasks.py       - Netzwerk + Hintergrund-Threads
    views.py       - Zeichnen (draw)
    controller.py  - Input (update) + init

Fuer den Einsatz auf der Konsole zu EINER Datei buendeln: build.py
erzeugt daraus apps/appstore.py (siehe README im Ordner).
"""
from .config import APP
from .controller import init, update
from .views import draw

__all__ = ["APP", "init", "update", "draw"]
