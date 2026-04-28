"""
py16.config
===========
Liest und schreibt ~/.py16/config.json.

Inhalt:
  carts_dir       - Pfad, in dem .p16/.pdf-Carts liegen
  boot_cart       - relativer Pfad zum Auto-Boot-Cart (oder None)
  power_off_cmd   - Shell-Kommando fuer Power-Off (Linux)
  reboot_cmd      - Shell-Kommando fuer Reboot
  boot_countdown  - Sekunden bis Auto-Boot (Default 3)
"""

import os
import json

DEFAULT_CONFIG = {
    "carts_dir":      "~/.py16/carts",
    "boot_cart":      "boot.p16",        # relativ zu carts_dir
    "power_off_cmd":  "sudo poweroff",
    "reboot_cmd":     "sudo reboot",
    "boot_countdown": 3,
    "fullscreen":     False,             # Bei True: SDL-Vollbild
    "display_scale":  "auto",            # "auto" oder ganzzahliger Faktor
    "hide_cursor":    "auto",            # "auto" (im Vollbild aus), True/False
}

CONFIG_DIR  = os.path.expanduser("~/.py16")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

_loaded_config = None

def get_config():
    """Liefert das aktuelle Config-Dict. Laedt es einmal lazy."""
    global _loaded_config
    if _loaded_config is not None:
        return _loaded_config

    # Override per Umgebungsvariable
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                user_cfg = json.load(f)
            cfg.update(user_cfg)
        except Exception as e:
            print(f"Config-Lesefehler ({CONFIG_PATH}): {e}")
    else:
        # Erststart: Default-Config schreiben
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            pass

    # Umgebungsvariable hat Vorrang
    env_dir = os.environ.get("PY16_CARTS_DIR")
    if env_dir:
        cfg["carts_dir"] = env_dir

    # Pfade expandieren
    cfg["carts_dir"] = os.path.expanduser(cfg["carts_dir"])

    # Cart-Verzeichnis sicherstellen
    try:
        os.makedirs(cfg["carts_dir"], exist_ok=True)
    except Exception:
        pass

    _loaded_config = cfg
    return cfg

def carts_dir():
    return get_config()["carts_dir"]

def boot_cart_path():
    """Voller Pfad zum Boot-Cart, oder None wenn nicht vorhanden."""
    cfg = get_config()
    if not cfg.get("boot_cart"):
        return None
    p = os.path.join(cfg["carts_dir"], cfg["boot_cart"])
    return p if os.path.exists(p) else None

def list_carts():
    """Listet alle .p16/.pdf-Dateien im Cart-Verzeichnis."""
    d = carts_dir()
    if not os.path.isdir(d):
        return []
    files = []
    for name in sorted(os.listdir(d)):
        full = os.path.join(d, name)
        if os.path.isfile(full):
            low = name.lower()
            if low.endswith(".p16") or low.endswith(".pdf"):
                files.append(full)
    return files

def reload_config():
    """Setzt den Config-Cache zurueck. Falls die Datei extern geaendert wurde."""
    global _loaded_config
    _loaded_config = None
