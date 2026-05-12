"""
py16.config
===========
Reads and writes ~/.py16/config.json.

Contents:
  carts_dir       - Path containing .p16/.pdf carts
  boot_cart       - relative path to auto-boot cart (or None)
  power_off_cmd   - Shell command for power-off (Linux)
  reboot_cmd      - Shell command for reboot
  boot_countdown  - Seconds until auto-boot (default 3)
"""

import os
import json

DEFAULT_CONFIG = {
    "carts_dir":      "~/.py16/carts",
    "boot_cart":      "boot.p16",        # relative to carts_dir
    "power_off_cmd":  "sudo poweroff",
    "reboot_cmd":     "sudo reboot",
    "boot_countdown": 3,
    "fullscreen":     False,             # If True: SDL fullscreen
    "display_scale":  "auto",            # "auto" or integer factor
    "hide_cursor":    "auto",            # "auto" (off in fullscreen), True/False
}

CONFIG_DIR  = os.path.expanduser("~/.py16")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

_loaded_config = None

def get_config():
    """Returns the current config dict. Loaded lazily."""
    global _loaded_config
    if _loaded_config is not None:
        return _loaded_config

    # Override via environment variable
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                user_cfg = json.load(f)
            cfg.update(user_cfg)
        except Exception as e:
            print(f"Config read error ({CONFIG_PATH}): {e}")
    else:
        # First run: write default config
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            pass

    # Environment variable takes precedence
    env_dir = os.environ.get("PY16_CARTS_DIR")
    if env_dir:
        cfg["carts_dir"] = env_dir

    # Expand paths
    cfg["carts_dir"] = os.path.expanduser(cfg["carts_dir"])

    # Ensure cart directory exists
    try:
        os.makedirs(cfg["carts_dir"], exist_ok=True)
    except Exception:
        pass

    _loaded_config = cfg
    return cfg

def carts_dir():
    return get_config()["carts_dir"]

def boot_cart_path():
    """Full path to boot cart, or None if not present."""
    cfg = get_config()
    if not cfg.get("boot_cart"):
        return None
    p = os.path.join(cfg["carts_dir"], cfg["boot_cart"])
    return p if os.path.exists(p) else None

def list_carts():
    """Lists all .p16/.pdf files in the cart directory."""
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
    """Resets the config cache. In case the file was changed externally."""
    global _loaded_config
    _loaded_config = None
