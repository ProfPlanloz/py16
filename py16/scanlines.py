"""
py16.scanlines
==============
HDMA-style scanline effects: shift each row of the screen horizontally
to make waves, tunnels, lens distortion, heat shimmer, and so on.

Like SNES HDMA, but applied as a single post-process step to the
finished framebuffer. Call `scanline_apply()` AFTER drawing the world
you want distorted, and BEFORE drawing HUD elements that should stay
straight.

Quick start:
    def draw():
        py16.cls(12)
        draw_world()                                # world tiles

        # Apply wave distortion to everything drawn so far:
        wave = py16.scanline_wave(time=frame, amplitude=4, frequency=0.1)
        py16.scanline_apply(x_offsets=wave)

        draw_hud()                                  # HUD on top, undistorted

Helpers (all return a list/array of HEIGHT offsets, one per scanline):
    py16.scanline_wave(time, amplitude, frequency, speed)
    py16.scanline_jitter(amplitude, seed)
    py16.scanline_lens(center_y, strength, radius)
    py16.scanline_interlace(odd_offset, even_offset)

Performance: with numpy, the apply step takes ~0.3 ms per frame on
desktop. Without numpy, ~5 ms - still fits in 60 FPS budget.
"""

import math
import random

import pygame

from . import state
from .core import WIDTH, HEIGHT

try:
    import numpy as _np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


# ======================================================================
# CORE APPLY
# ======================================================================

def scanline_apply(x_offsets=None, wrap=False, fill_color=0):
    """Shift each row of the screen horizontally by x_offsets[row].

    x_offsets : list/array of HEIGHT integer offsets (one per row).
                Positive = shift right, negative = shift left.
                If shorter than HEIGHT, missing rows have offset 0.
                If None, no effect.
    wrap      : if True, pixels that fall off one edge reappear on the
                opposite edge (good for seamless wave loops). Default False.
    fill_color: palette index used to fill the gap left by a shifted row
                (only when wrap=False). Default 0 (black).
    """
    if x_offsets is None or state.screen is None:
        return

    if _HAS_NUMPY:
        _apply_numpy(x_offsets, wrap, fill_color)
    else:
        _apply_python(x_offsets, wrap, fill_color)


def _apply_numpy(x_offsets, wrap, fill_color):
    # Capture current screen pixels into a numpy array (W, H, 3)
    src_view = pygame.surfarray.array3d(state.screen)   # (W, H, 3)
    src = src_view.copy()
    dst = src.copy()

    # Convert offsets to int32 numpy array, pad/truncate to HEIGHT
    offs = _np.asarray(x_offsets, dtype=_np.int32)
    if len(offs) < HEIGHT:
        offs = _np.concatenate([offs, _np.zeros(HEIGHT - len(offs),
                                                dtype=_np.int32)])
    elif len(offs) > HEIGHT:
        offs = offs[:HEIGHT]

    from .core import PALETTE
    fill_rgb = PALETTE[fill_color & 0xFF]

    if wrap:
        # Each row: roll horizontally
        for y in range(HEIGHT):
            ox = int(offs[y])
            if ox == 0:
                continue
            dst[:, y, :] = _np.roll(src[:, y, :], ox, axis=0)
    else:
        # Each row: shift with edge-fill
        for y in range(HEIGHT):
            ox = int(offs[y])
            if ox == 0:
                continue
            if ox > 0:
                # Shift right: gap on the left
                if ox < WIDTH:
                    dst[ox:, y, :] = src[:WIDTH - ox, y, :]
                    dst[:ox, y, :] = fill_rgb
                else:
                    dst[:, y, :] = fill_rgb
            else:
                # Shift left: gap on the right
                ox = -ox
                if ox < WIDTH:
                    dst[:WIDTH - ox, y, :] = src[ox:, y, :]
                    dst[WIDTH - ox:, y, :] = fill_rgb
                else:
                    dst[:, y, :] = fill_rgb

    # Push the modified array back to the screen surface
    pygame.surfarray.blit_array(state.screen, dst)


def _apply_python(x_offsets, wrap, fill_color):
    """Slower fallback: use pygame.Surface.scroll per row. Limited to
    integer offsets and a single screen-sized scratch surface."""
    from .core import PALETTE
    fill_rgb = PALETTE[fill_color & 0xFF]

    # Take a snapshot, then redraw row-shifted on the original
    src = state.screen.copy()

    for y in range(min(HEIGHT, len(x_offsets))):
        ox = int(x_offsets[y])
        if ox == 0:
            continue
        # 1-pixel-high source rect
        src_rect = pygame.Rect(0, y, WIDTH, 1)

        if wrap:
            # Two blits to wrap
            state.screen.fill((0, 0, 0), (0, y, WIDTH, 1))
            state.screen.blit(src, (ox, y), src_rect)
            if ox > 0:
                state.screen.blit(src, (ox - WIDTH, y), src_rect)
            else:
                state.screen.blit(src, (ox + WIDTH, y), src_rect)
        else:
            state.screen.fill(fill_rgb, (0, y, WIDTH, 1))
            state.screen.blit(src, (ox, y), src_rect)


# ======================================================================
# SCANLINE EFFECT HELPERS
# ======================================================================

def scanline_wave(time, amplitude=4.0, frequency=0.1, speed=2.0,
                  y_start=0, y_end=None):
    """Smooth sine-wave horizontal offset.

    time      : current frame or any monotonic float
    amplitude : peak shift in pixels (4 = subtle, 16 = dramatic)
    frequency : controls how dense the wave is (lower = wider waves)
    speed     : how fast the wave scrolls vertically with time
    y_start   : first row to affect (0 = top). Use this to only wave the
                water area below the horizon, for example.
    y_end     : last row + 1 (None = HEIGHT)
    """
    if y_end is None:
        y_end = HEIGHT
    n_rows = HEIGHT
    if _HAS_NUMPY:
        out = _np.zeros(n_rows, dtype=_np.float32)
        idx = _np.arange(y_start, y_end, dtype=_np.float32)
        out[y_start:y_end] = amplitude * _np.sin(idx * frequency + time * speed * 0.01)
        return out
    out = [0.0] * n_rows
    for y in range(y_start, y_end):
        out[y] = amplitude * math.sin(y * frequency + time * speed * 0.01)
    return out


def scanline_jitter(amplitude=2, seed=None, y_start=0, y_end=None):
    """Random per-row jitter, like TV static or heat distortion."""
    if y_end is None:
        y_end = HEIGHT
    n_rows = HEIGHT
    rng = random.Random(seed) if seed is not None else random
    if _HAS_NUMPY and seed is not None:
        np_rng = _np.random.default_rng(seed)
        out = _np.zeros(n_rows, dtype=_np.float32)
        out[y_start:y_end] = np_rng.uniform(-amplitude, amplitude,
                                             y_end - y_start)
        return out
    out = [0.0] * n_rows
    for y in range(y_start, y_end):
        out[y] = rng.uniform(-amplitude, amplitude)
    return out


def scanline_lens(center_y, strength=8.0, radius=40, y_start=0, y_end=None):
    """Convex-lens distortion centered around screen-y `center_y`.

    Rows close to center_y are shifted outward (creating a bulge).
    Use for boss-aura effects, magic glow, fish-eye lens.

    strength : peak offset in pixels at the lens edge
    radius   : how many rows away from center the effect extends
    """
    if y_end is None:
        y_end = HEIGHT
    n_rows = HEIGHT
    if _HAS_NUMPY:
        idx = _np.arange(n_rows, dtype=_np.float32)
        dist = idx - center_y
        # Gaussian-ish profile that peaks at +/- radius/2 from center
        normalized = dist / max(1, radius)
        # Sin profile: 0 at center, peak at ±1, zero outside
        amplitude = _np.where(
            _np.abs(normalized) <= 1.0,
            _np.sin(normalized * math.pi) * strength,
            0.0,
        )
        out = _np.zeros(n_rows, dtype=_np.float32)
        out[y_start:y_end] = amplitude[y_start:y_end]
        return out
    out = [0.0] * n_rows
    for y in range(y_start, y_end):
        dist = y - center_y
        normalized = dist / max(1, radius)
        if abs(normalized) <= 1.0:
            out[y] = math.sin(normalized * math.pi) * strength
    return out


def scanline_interlace(odd_offset=1, even_offset=-1,
                       y_start=0, y_end=None):
    """Alternate rows shift opposite directions, creating a CRT-like
    interlace artifact. Use sparingly - it's harsh but very retro."""
    if y_end is None:
        y_end = HEIGHT
    n_rows = HEIGHT
    if _HAS_NUMPY:
        out = _np.zeros(n_rows, dtype=_np.float32)
        idx = _np.arange(y_start, y_end)
        out[y_start:y_end] = _np.where(idx % 2 == 0, even_offset, odd_offset)
        return out
    out = [0.0] * n_rows
    for y in range(y_start, y_end):
        out[y] = even_offset if y % 2 == 0 else odd_offset
    return out


def scanline_pinch(time, amplitude=2.0, period=60.0,
                   y_start=0, y_end=None):
    """Full-screen pinch: smoothly bulge in and out over time.
    Period is in frames (60 = 1 sec at 60 FPS)."""
    if y_end is None:
        y_end = HEIGHT
    center = (y_start + y_end) / 2
    radius = (y_end - y_start) / 2
    strength = amplitude * math.sin(time / period * 2 * math.pi)
    return scanline_lens(center, strength=strength, radius=radius,
                         y_start=y_start, y_end=y_end)
