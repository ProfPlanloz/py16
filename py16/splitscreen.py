"""
py16.splitscreen
================
Couch-multiplayer splitscreen: render each player into their own
viewport with their own camera, then draw a shared HUD over the top.

Quick start:
    def draw():
        py16.cls(0)                           # whole screen
        py16.split_layout("horizontal")       # 2 viewports side-by-side
        for p in range(2):
            py16.viewport(p + 1)              # 1 = left, 2 = right
            py16.camera(player_x[p] - 64,
                        player_y[p] - 56)
            draw_world()                      # only draws inside this viewport
            draw_player(p)
        py16.viewport(0)                      # full screen again
        draw_hud()                            # shared HUD over both views

Layouts:
    "full"        : viewport 1 = full screen (default)
    "horizontal"  : viewport 1 = left half, viewport 2 = right half
    "vertical"    : viewport 1 = top half, viewport 2 = bottom half
    "quad"        : 2x2 grid (1=TL, 2=TR, 3=BL, 4=BR) for 3-4 players

Viewport 0 always means "the full screen" (used for HUD overlays).
Coordinates inside a viewport are in WORLD space - the same as before,
just clipped to the viewport region. The camera tells you where in
the world to look from.

Each viewport has its own camera. Switching viewport restores its
camera; setting `camera()` after `viewport(N)` updates that viewport's
camera.
"""

import pygame

from . import state
from .core import WIDTH, HEIGHT

# ======================================================================
# LAYOUT DEFINITIONS
# ======================================================================

def _layout_rects(mode):
    """Return a list of (x, y, w, h) rects in screen pixels for the
    given layout mode. Index 0 is always the full screen for the HUD."""
    if mode == "full":
        return [
            (0, 0, WIDTH, HEIGHT),    # 0 = full (HUD)
            (0, 0, WIDTH, HEIGHT),    # 1 = same as full
        ]
    if mode == "horizontal":
        half = WIDTH // 2
        return [
            (0, 0, WIDTH, HEIGHT),
            (0, 0, half, HEIGHT),         # 1 = left
            (half, 0, WIDTH - half, HEIGHT),  # 2 = right
        ]
    if mode == "vertical":
        half = HEIGHT // 2
        return [
            (0, 0, WIDTH, HEIGHT),
            (0, 0, WIDTH, half),          # 1 = top
            (0, half, WIDTH, HEIGHT - half),  # 2 = bottom
        ]
    if mode == "quad":
        hw = WIDTH // 2
        hh = HEIGHT // 2
        return [
            (0, 0, WIDTH, HEIGHT),
            (0, 0, hw, hh),               # 1 = top-left
            (hw, 0, WIDTH - hw, hh),      # 2 = top-right
            (0, hh, hw, HEIGHT - hh),     # 3 = bottom-left
            (hw, hh, WIDTH - hw, HEIGHT - hh),  # 4 = bottom-right
        ]
    # Unknown layout - fall back to full
    return _layout_rects("full")

# ======================================================================
# STATE INIT
# ======================================================================

def _ensure_state():
    if not hasattr(state, "viewport_layout"):
        state.viewport_layout = "full"
        state.viewport_rects = _layout_rects("full")
        # Per-viewport camera state. Index 0 is "no viewport active /
        # full screen", index 1..4 are the player views.
        state.viewport_cameras = [(0, 0) for _ in range(5)]
        state.active_viewport = 0

# ======================================================================
# PUBLIC API
# ======================================================================

def split_layout(mode="full"):
    """Set the splitscreen layout mode.

    mode : "full" | "horizontal" | "vertical" | "quad"

    After calling this, use viewport(N) to render into each viewport.
    Resets the active viewport to 0 (full screen).
    """
    _ensure_state()
    state.viewport_layout = mode
    state.viewport_rects = _layout_rects(mode)
    # Reset per-viewport cameras to (0, 0)
    state.viewport_cameras = [(0, 0) for _ in range(5)]
    viewport(0)

def viewport(idx=0):
    """Activate viewport N.

    idx=0     : full screen (no clipping). Used for HUD on top.
    idx=1..4  : that player's viewport. Sets clip rect, applies that
                viewport's saved camera. The clip rect ensures draws
                outside this viewport are discarded.

    Switching viewport saves the previous viewport's user-camera,
    restores the new one. Subsequent camera() calls modify the active
    viewport's user-camera.
    """
    _ensure_state()

    # Save the *user-facing* camera of the current viewport, by undoing
    # the viewport-offset bake-in. This lets camera() / viewport() pairs
    # round-trip without drift.
    if 0 <= state.active_viewport < len(state.viewport_cameras):
        cur_rect = state.viewport_rects[state.active_viewport]
        if state.active_viewport == 0:
            user_cam_x = state.cam_x
            user_cam_y = state.cam_y
        else:
            user_cam_x = state.cam_x + cur_rect[0]
            user_cam_y = state.cam_y + cur_rect[1]
        state.viewport_cameras[state.active_viewport] = \
            (user_cam_x, user_cam_y)

    # Clamp to valid range
    if idx < 0 or idx >= len(state.viewport_rects):
        idx = 0
    state.active_viewport = idx

    # Set the clip rect to the viewport bounds (idx=0 = full = no clip)
    rect = state.viewport_rects[idx]
    if idx == 0:
        state.screen.set_clip(None)
        state.viewport_clip = None
    else:
        state.screen.set_clip(rect)
        state.viewport_clip = rect

    # Apply the new viewport's saved camera (re-bake with new offset)
    user_cam = state.viewport_cameras[idx]
    if idx == 0:
        state.cam_x = user_cam[0]
        state.cam_y = user_cam[1]
    else:
        state.cam_x = user_cam[0] - rect[0]
        state.cam_y = user_cam[1] - rect[1]

def for_each_player(callback, n=None):
    """Convenience: call `callback(player_idx)` for each active player
    viewport (1..N). If n is None, uses the number of viewports in
    the current layout (excluding the full-screen overlay slot 0).

    Example:
        py16.split_layout("horizontal")
        py16.for_each_player(lambda p: draw_player_view(p))
        py16.viewport(0)
        draw_hud()
    """
    _ensure_state()
    if n is None:
        n = len(state.viewport_rects) - 1
    for p in range(1, n + 1):
        viewport(p)
        callback(p)

def viewport_rect(idx=None):
    """Returns the (x, y, w, h) rect of the given viewport in screen
    pixels. None = the active viewport. Useful for placing per-viewport
    HUD or testing if a world position is visible in this viewport."""
    _ensure_state()
    if idx is None:
        idx = state.active_viewport
    if 0 <= idx < len(state.viewport_rects):
        return state.viewport_rects[idx]
    return (0, 0, WIDTH, HEIGHT)

def num_viewports():
    """Returns how many player viewports exist in the current layout
    (excluding the slot 0 full-screen). 1 for "full", 2 for horizontal
    or vertical, 4 for quad."""
    _ensure_state()
    return max(1, len(state.viewport_rects) - 1)

def viewport_local(x, y, idx=None):
    """Convert viewport-local coordinates (where 0,0 is the top-left of
    the viewport) to WORLD coordinates. Pass these to text/spr/etc and
    they'll appear at that local position inside the viewport,
    regardless of the active camera.

    Example - draw a per-viewport HUD label that stays put even while
    the camera scrolls the world:
        py16.viewport(1)
        py16.camera(player_x - 64, player_y - 56)
        draw_world()                # uses camera
        wx, wy = py16.viewport_local(4, 4)
        py16.text("P1", wx, wy, 11)   # stays at top-left of viewport 1
    """
    _ensure_state()
    if idx is None:
        idx = state.active_viewport
    if 0 <= idx < len(state.viewport_rects):
        rect = state.viewport_rects[idx]
        # Screen position of (x, y) inside this viewport
        sx = rect[0] + x
        sy = rect[1] + y
        # World coordinate that lands at this screen position
        # given the engine subtracts cam internally:
        # screen = world - cam  =>  world = screen + cam
        return (sx + state.cam_x, sy + state.cam_y)
    return (x, y)
