# py16os Plugin App Cheatsheet for AI Assistants

> **Use this as a system prompt when asking an AI to write a plugin app for
> the py16os desktop cart.** The host cart already runs on py-16 and provides
> the window manager, taskbar, drag/drop, theme, and language system.
> Your plugin only fills the **inside** of a window.

## What a plugin is

A plugin is a single `.py` file dropped into the `apps/` folder next to
`py16os.py`. On startup the cart scans `apps/`, loads each plugin, gives it a
window, and adds a desktop icon. Reload without restart with the terminal
command `RELOAD`.

## Minimum skeleton (every plugin needs this)

```python
# apps/myapp.py
APP = {
    "id": "myapp",          # unique; must NOT collide with builtins
    "name": "MYAPP",        # shown on icon + window title (upper-cased, max ~10)
    "w": 120, "h": 90,      # initial window size in pixels
    "resizable": False,     # if True, also set min_w / min_h
    # "min_w": 80, "min_h": 60,
    # "icon": "myapp.p16img",   # optional explicit icon path (rel. to apps/)
}

def init(win):
    """Called ONCE when the plugin is registered. Set up state in win[...]"""
    win["counter"] = 0

def update(win, lx, ly, m_pressed, m_sec_pressed, m_held):
    """Called every frame while the window is the foreground (active) one."""
    if m_pressed:
        win["counter"] += 1

def draw(win, wx, wy, ww, wh, is_active):
    """Called every frame while the window is visible. Draw inside the window."""
    import py16
    py16.text("CLICKS: " + str(win["counter"]), wx + 6, wy + 18, 1)
```

No `if __name__ == "__main__"`, no `py16.run(...)`. The host already runs
the event loop and dispatches to your `update` / `draw`.

## APP dict fields

| Field        | Type | Default | Notes                                          |
|--------------|------|---------|------------------------------------------------|
| `id`         | str  | —       | Required. Lower-case, no spaces. Unique.       |
| `name`       | str  | id      | Display name. Auto-uppercased, truncated to 10.|
| `w`, `h`     | int  | 140,110 | Initial window size in px.                     |
| `resizable`  | bool | False   | If True, user can resize.                      |
| `min_w`,`min_h`| int| 60,50  | Minimum size when resizable.                   |
| `icon`       | str  | —       | Optional `.p16img` filename (rel. to `apps/`). |

**Icon resolution order** (highest priority first):

1. User-assigned: `.p16img` dropped onto the desktop icon (persisted in `theme.json`).
2. Explicit: `APP["icon"]` in your dict.
3. Convention: `apps/<plugin-filename>.p16img` (e.g. `apps/myapp.p16img` for `apps/myapp.py`).
4. Convention: `apps/<app-id>.p16img`.
5. Generic fallback icon drawn by the OS.

## Lifecycle

```
load                          first-ever start: init(win) once
        ↓
event loop (60 FPS) ─→ update(win, lx, ly, m_pressed, m_sec_pressed, m_held)
                  └─→ draw(win, wx, wy, ww, wh, is_active)
                  └─→ (next frame...)
```

* `init` is optional. If you set up data here, it survives only while the
  cart is running. To persist data across restarts, write a file yourself
  (see *Persistence* below).
* `update` is only called when the window is the **foreground** (top of
  z-order). Don't rely on it ticking when buried under other windows.
* `draw` is called whenever the window is visible (even when not focused).
  Pure drawing — no game logic, no state changes.

## Coordinates: the one thing to get right

```
   wx,wy ────────── ww ─────────────┐
   │                                │
   │  ↑  ly = 0 here                │
   │  │                             │  wh
   │  │  ← lx = 0 at wx               │
   │                                │
   └────────────────────────────────┘
```

* In `draw`: use **absolute** screen coords. The window's top-left is
  `(wx, wy)`. Draw at `wx + offset_x, wy + offset_y`.
* In `update`: `lx, ly` are already **local** to the window. Hit-test like
  `if 6 <= lx <= 40 and 20 <= ly <= 28: ...`.
* The OS draws the title bar (the top ~12 px). Stay below `wy + 14` in draw,
  and ignore `ly < 14` in update if you want to be safe.

## Input

`update` receives three boolean-ish flags computed by the OS — they unify
mouse and gamepad input, so you don't have to handle them separately:

* `m_pressed` — primary click/tap edge this frame (left mouse / Z / Space).
* `m_sec_pressed` — secondary click edge (right mouse / X).
* `m_held` — primary held down (for drag, paint strokes, etc.).

Don't poll `py16.mouse_*` or `py16.btn*` directly inside `update`. The OS
gives you everything you need via `lx, ly` + the three flags.

## Storing state: use the `win` dict

```python
def init(win):
    win["score"] = 0
    win["items"] = ["apple", "bread", "milk"]

def update(win, lx, ly, mp, msp, mh):
    if mp: win["score"] += 1

def draw(win, wx, wy, ww, wh, active):
    py16.text(str(win["score"]), wx + 6, wy + 18, 1)
```

Never use module-level globals for per-window state. If the user closes and
reopens the window, the dict persists. If you use globals, you'll leak
between sessions and break if the cart ever runs two instances.

The OS reserves these `win` keys: `id`, `title`, `x`, `y`, `w`, `h`,
`visible`, `minimized`, `resizable`, `min_w`, `min_h`, `_plugin`. Don't
overwrite them or your window will misbehave.

## Drawing reference (the common subset of py-16)

```python
import py16   # do this once at the top of your plugin

# Display constants
py16.WIDTH       # 256
py16.HEIGHT      # 224

# Solid drawing — c is a palette index 0-15 inside the cart
py16.rectfill(x, y, w, h, c)
py16.rect(x, y, w, h, c)
py16.line(x0, y0, x1, y1, c)
py16.pset(x, y, c)
py16.circ(x, y, r, c)
py16.circfill(x, y, r, c)

# Text — 3x5 pixel font, always upper-case looking
py16.text("HELLO", x, y, c)

# Clipping (use to prevent drawing past your window border)
py16.clip(x, y, w, h)   # set scissor box
py16.clip()             # reset to fullscreen

# Sound (use sparingly — host already plays UI sounds)
py16.tone(880, 10, py16.WAVE_SQUARE)
```

The host palette uses indices **0–15**. Color 7 is the "window background"
and is treated as transparent when used in icon images (`.p16img`).

## Talking to the user: translations

If your plugin shows labels that should follow the user's chosen language,
call the OS helper `tr(key)`:

```python
def draw(win, wx, wy, ww, wh, active):
    import py16
    # The host has a global `tr`; access it through the module that imports it.
    # Simplest: hard-code English in your plugin and let the user add a JSON
    # key like "MYAPP:BUTTON" to lang/de.json. Then:
    from __main__ import tr   # works because the host module is the entry point
    py16.text(tr("MYAPP:BUTTON"), wx + 6, wy + 18, 1)
```

If `tr()` doesn't find the key, it returns the key itself, so the English
literal is always the safe fallback. Use namespaced keys (`MYAPP:HELLO`)
to avoid collisions with OS strings (`DELETE`, `YES`, `NO`, …).

## Persistence

The `win` dict is in-memory only. To remember things across cart restarts,
write your own file next to the cart:

```python
import json, os
SAVE_PATH = "myapp_save.json"

def _save(win):
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump({"score": win["score"]}, f)
    except Exception: pass

def init(win):
    win["score"] = 0
    if os.path.isfile(SAVE_PATH):
        try:
            with open(SAVE_PATH) as f:
                win["score"] = json.load(f).get("score", 0)
        except Exception: pass
```

Be a good citizen: namespace your filename (`myapp_save.json`, not
`save.json`) and tolerate read failures.

## Crashes are contained

Every plugin `update` / `draw` runs inside a safety wrapper. If your code
raises, the OS keeps running and your window shows a red `PLUGIN ERROR`
box with the exception message — the rest of the desktop is unaffected.
You can use this for quick debugging: just `raise` what you want to see.

## What you cannot do

* Don't import or call `py16.run()` — the host already owns the event loop.
* Don't reuse an `id` that already belongs to a builtin (`files`, `notepad`,
  `paint`, `music`, `terminal`, `calc`, `colors`) — registration is refused.
* Don't draw a title bar, close button, or window border — the OS does that.
* Don't call `eval` / `exec` on user-supplied strings. The CALC app uses
  a small AST-based safe evaluator (`safe_eval`) for arithmetic; copy that
  pattern if you need expressions.
* Don't `pygame.mixer.music.load(...)` something the user didn't ask for.
  Use `py16.tone(...)` for UI feedback.
* Don't block. There is no `time.sleep`-friendly loop here. Use frame
  counters (`win["t"] = win.get("t", 0) + 1`) instead.

## Two complete examples

### 1. A clicker counter

```python
# apps/clicker.py
APP = {"id": "clicker", "name": "CLICK", "w": 100, "h": 60}

def init(win):
    win["n"] = 0

def update(win, lx, ly, mp, msp, mh):
    if mp and 6 <= lx <= 94 and 30 <= ly <= 50:
        win["n"] += 1

def draw(win, wx, wy, ww, wh, active):
    import py16
    py16.text("SCORE: " + str(win["n"]), wx + 6, wy + 18, 1)
    py16.rectfill(wx + 6, wy + 30, 88, 20, 5)
    py16.rect(wx + 6, wy + 30, 88, 20, 0)
    py16.text("CLICK ME", wx + 32, wy + 36, 7)
```

### 2. A digital clock with seconds

```python
# apps/clock.py
import time
APP = {"id": "clock", "name": "CLOCK", "w": 90, "h": 36}

def update(win, lx, ly, mp, msp, mh):
    pass   # nothing to do — time updates itself in draw

def draw(win, wx, wy, ww, wh, active):
    import py16
    t = time.localtime()
    s = "%02d:%02d:%02d" % (t.tm_hour, t.tm_min, t.tm_sec)
    py16.text(s, wx + (ww - len(s) * 4) // 2, wy + 18, 1)
```

Drop those two files into `apps/`, start the cart, and both appear on the
desktop and in the start menu.

## Quick checklist before shipping

* [ ] `APP["id"]` is unique, lower-case, no spaces.
* [ ] `update` accepts exactly `(win, lx, ly, m_pressed, m_sec_pressed, m_held)`.
* [ ] `draw` accepts exactly `(win, wx, wy, ww, wh, is_active)`.
* [ ] All draw coordinates are `wx + dx, wy + dy` — never raw `dx, dy`.
* [ ] State lives in `win[...]`, not module globals.
* [ ] No reserved `win` keys are overwritten.
* [ ] Optional: a `<plugin>.p16img` next to your `.py` for a custom icon.
* [ ] Optional: namespaced translation keys (`MYAPP:HELLO`) for `lang/*.json`.
