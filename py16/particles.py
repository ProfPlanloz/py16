"""
py16.particles
==============
Particle system for fire, smoke, sparks, explosions, trails, confetti.

Quick start:
    # One-shot particle
    py16.particle(x, y, vx, vy, life=60, color=10)

    # Burst (explosion-style)
    py16.burst(x, y, count=30, color=8, life=30, speed=2.5)

    # Continuous emission via Emitter
    fire = py16.Emitter(x=100, y=200, rate=8, ...)
    fire.update()
    fire.draw()

    # Required once per frame in your draw():
    py16.particles_update()
    py16.particles_draw()

Performance:
    With numpy installed, 2000 particles run at 60+ FPS on a Pi 4.
    Without numpy, the fallback handles ~500 comfortably.

Blending:
    Each particle can specify a blend mode ("normal" | "add" | "sub" | "alpha").
    Sorting particles by blend reduces state changes.
"""

import math
import random

import pygame

from . import state
from .core import WIDTH, HEIGHT, color_rgb

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ======================================================================
# CONSTANTS
# ======================================================================

MAX_PARTICLES = 2000

# Field indices in the per-particle data arrays (when using numpy)
F_X     = 0
F_Y     = 1
F_VX    = 2
F_VY    = 3
F_AX    = 4
F_AY    = 5
F_LIFE  = 6   # remaining frames; <=0 means dead
F_LIFE0 = 7   # initial lifetime (for fade calculations)
F_SIZE  = 8   # radius in pixels
F_COLOR = 9   # palette index 0..255
F_BLEND = 10  # 0=normal, 1=add, 2=sub, 3=alpha
F_DRAG  = 11  # multiplied into velocity each frame (1.0 = no drag)
N_FIELDS = 12

BLEND_NORMAL = 0
BLEND_ADD    = 1
BLEND_SUB    = 2
BLEND_ALPHA  = 3

_BLEND_STR_TO_INT = {
    "normal": BLEND_NORMAL,
    "add":    BLEND_ADD,
    "sub":    BLEND_SUB,
    "alpha":  BLEND_ALPHA,
}
_BLEND_INT_TO_STR = {v: k for k, v in _BLEND_STR_TO_INT.items()}

# ======================================================================
# STATE
# ======================================================================

def _ensure_state():
    if not hasattr(state, "particles_data") or state.particles_data is None:
        if _HAS_NUMPY:
            state.particles_data = np.zeros((MAX_PARTICLES, N_FIELDS),
                                            dtype=np.float32)
            state.particles_alive = np.zeros(MAX_PARTICLES, dtype=bool)
        else:
            state.particles_data = [None] * MAX_PARTICLES
            state.particles_alive = [False] * MAX_PARTICLES
        state.particles_next_slot = 0

# ======================================================================
# CORE API
# ======================================================================

def _normalize_blend(blend):
    if isinstance(blend, str):
        return _BLEND_STR_TO_INT.get(blend, BLEND_NORMAL)
    return int(blend) if blend in (0, 1, 2, 3) else BLEND_NORMAL

def _free_slot():
    """Find an unused particle slot, or recycle the oldest one."""
    _ensure_state()
    start = state.particles_next_slot
    n = MAX_PARTICLES
    if _HAS_NUMPY:
        # Try fast: are any slots not alive?
        idx_arr = np.where(~state.particles_alive)[0]
        if len(idx_arr) > 0:
            state.particles_next_slot = (int(idx_arr[0]) + 1) % n
            return int(idx_arr[0])
        # All slots full - recycle next-slot pointer
        slot = start
        state.particles_next_slot = (start + 1) % n
        return slot
    # Python fallback
    for off in range(n):
        slot = (start + off) % n
        if not state.particles_alive[slot]:
            state.particles_next_slot = (slot + 1) % n
            return slot
    slot = start
    state.particles_next_slot = (start + 1) % n
    return slot

def particle(x, y, vx=0, vy=0, life=60, color=7,
             size=1, ax=0.0, ay=0.0, drag=1.0, blend="normal"):
    """Spawn a single particle.

    x, y      : starting position (world coords)
    vx, vy    : initial velocity in pixels/frame
    life      : lifetime in frames (60 = 1 second at 60 FPS)
    color     : palette index for the particle color
    size      : radius in pixels (rounded, min 1)
    ax, ay    : constant acceleration (e.g. ay=0.1 for gravity)
    drag      : velocity multiplier per frame (0.95 = slows down)
    blend     : "normal" | "add" | "sub" | "alpha"
    """
    _ensure_state()
    slot = _free_slot()
    b = _normalize_blend(blend)
    if _HAS_NUMPY:
        d = state.particles_data[slot]
        d[F_X]     = x
        d[F_Y]     = y
        d[F_VX]    = vx
        d[F_VY]    = vy
        d[F_AX]    = ax
        d[F_AY]    = ay
        d[F_LIFE]  = life
        d[F_LIFE0] = life
        d[F_SIZE]  = max(1, int(size))
        d[F_COLOR] = int(color) & 0xFF
        d[F_BLEND] = b
        d[F_DRAG]  = drag
        state.particles_alive[slot] = True
    else:
        state.particles_data[slot] = [
            float(x), float(y), float(vx), float(vy),
            float(ax), float(ay), float(life), float(life),
            max(1, int(size)), int(color) & 0xFF, b, float(drag),
        ]
        state.particles_alive[slot] = True

def burst(x, y, count=20, color=8, life=30, speed=2.0, size=1,
          spread_angle=2 * math.pi, base_angle=0.0,
          ax=0.0, ay=0.0, drag=1.0, blend="normal",
          speed_var=0.5, life_var=0.5):
    """Spawn a burst of particles radiating from (x, y).

    count        : how many particles
    speed        : average outward speed (pixels/frame)
    spread_angle : angular cone (radians). 2*pi = full circle (default).
    base_angle   : center direction of cone. 0 = right.
    speed_var    : ±fraction added to speed (0.5 = ±50%)
    life_var     : ±fraction added to lifetime
    Other params are passed through to particle().
    """
    half = spread_angle / 2
    for _ in range(count):
        ang = base_angle + random.uniform(-half, half)
        s = speed * (1.0 + random.uniform(-speed_var, speed_var))
        vx = math.cos(ang) * s
        vy = math.sin(ang) * s
        L = int(life * (1.0 + random.uniform(-life_var, life_var)))
        particle(x, y, vx, vy, life=max(1, L), color=color,
                 size=size, ax=ax, ay=ay, drag=drag, blend=blend)

def particles_clear():
    """Remove all live particles."""
    _ensure_state()
    if _HAS_NUMPY:
        state.particles_alive[:] = False
    else:
        for i in range(MAX_PARTICLES):
            state.particles_alive[i] = False

def particles_count():
    """Number of currently live particles."""
    _ensure_state()
    if _HAS_NUMPY:
        return int(state.particles_alive.sum())
    return sum(1 for a in state.particles_alive if a)

# ======================================================================
# UPDATE (called once per frame)
# ======================================================================

def particles_update():
    """Advance physics for all live particles. Call once per frame
    (in your update() or top of your draw())."""
    _ensure_state()
    if _HAS_NUMPY:
        _update_numpy()
    else:
        _update_python()

def _update_numpy():
    alive = state.particles_alive
    if not alive.any():
        return
    d = state.particles_data
    # Apply acceleration to velocity
    d[alive, F_VX] += d[alive, F_AX]
    d[alive, F_VY] += d[alive, F_AY]
    # Apply drag
    d[alive, F_VX] *= d[alive, F_DRAG]
    d[alive, F_VY] *= d[alive, F_DRAG]
    # Apply velocity to position
    d[alive, F_X] += d[alive, F_VX]
    d[alive, F_Y] += d[alive, F_VY]
    # Decrement life
    d[alive, F_LIFE] -= 1
    # Kill expired
    state.particles_alive = alive & (d[:, F_LIFE] > 0)

def _update_python():
    for i in range(MAX_PARTICLES):
        if not state.particles_alive[i]:
            continue
        p = state.particles_data[i]
        p[F_VX] += p[F_AX]
        p[F_VY] += p[F_AY]
        p[F_VX] *= p[F_DRAG]
        p[F_VY] *= p[F_DRAG]
        p[F_X]  += p[F_VX]
        p[F_Y]  += p[F_VY]
        p[F_LIFE] -= 1
        if p[F_LIFE] <= 0:
            state.particles_alive[i] = False

# ======================================================================
# DRAW (called once per frame)
# ======================================================================

def particles_draw():
    """Render all live particles to the screen. Grouped by blend mode
    to minimise state changes."""
    _ensure_state()
    from .graphics import circfill, pset, blend_mode

    if _HAS_NUMPY:
        alive_idx = np.where(state.particles_alive)[0]
        if len(alive_idx) == 0:
            return
        data = state.particles_data
        # Group particles by blend mode for fewer state switches
        for blend_int in (BLEND_NORMAL, BLEND_ADD, BLEND_SUB, BLEND_ALPHA):
            mask = data[alive_idx, F_BLEND] == blend_int
            if not mask.any():
                continue
            blend_mode(_BLEND_INT_TO_STR[blend_int])
            for slot in alive_idx[mask]:
                d = data[slot]
                _draw_one(int(d[F_X]), int(d[F_Y]),
                          int(d[F_SIZE]), int(d[F_COLOR]),
                          d[F_LIFE], d[F_LIFE0])
        blend_mode("normal")
    else:
        # Python fallback - one-by-one with blend switch on change
        last_blend = -1
        for i in range(MAX_PARTICLES):
            if not state.particles_alive[i]:
                continue
            p = state.particles_data[i]
            b = int(p[F_BLEND])
            if b != last_blend:
                blend_mode(_BLEND_INT_TO_STR[b])
                last_blend = b
            _draw_one(int(p[F_X]), int(p[F_Y]),
                      int(p[F_SIZE]), int(p[F_COLOR]),
                      p[F_LIFE], p[F_LIFE0])
        blend_mode("normal")

def _draw_one(x, y, size, color, life, life0):
    """Draw a single particle. If size==1, use pset; else circfill."""
    from .graphics import circfill, pset
    if size <= 1:
        pset(x, y, color)
    else:
        circfill(x, y, size, color)

# ======================================================================
# EMITTER (continuous emission)
# ======================================================================

class Emitter:
    """Continuous particle source. Useful for fire, smoke, fountain, etc.

    Example - flickering torch:
        torch = py16.Emitter(x=100, y=180,
                             rate=4,                # particles per frame
                             life=30, life_var=0.3,
                             color=10,              # yellow
                             size=2,
                             vy=-2, vy_var=0.3,
                             vx_var=0.5,
                             ay=-0.05,              # particles rise
                             blend="add")
        # In your update():
        torch.update()
        # In your draw() (or do this from update):
        # The global py16.particles_draw() picks it up automatically.

    Set emit=False to pause emission without stopping existing particles.
    """

    def __init__(self, x=0, y=0, rate=1,
                 life=60, life_var=0.2,
                 vx=0.0, vy=0.0, vx_var=0.0, vy_var=0.0,
                 ax=0.0, ay=0.0, drag=1.0,
                 color=7, color_list=None,
                 size=1, blend="normal"):
        self.x = x
        self.y = y
        self.rate = rate           # particles per frame (can be < 1)
        self.life = life
        self.life_var = life_var
        self.vx = vx
        self.vy = vy
        self.vx_var = vx_var
        self.vy_var = vy_var
        self.ax = ax
        self.ay = ay
        self.drag = drag
        self.color = color
        # If color_list is set, pick a random color from it for each particle.
        # Use this instead of color_var for stylistic palettes like fire
        # ([8, 9, 10] = red/orange/yellow) - palette indices in py-16 are
        # NOT hue-sorted, so adding ±N to color does NOT produce a shimmer.
        self.color_list = color_list
        self.size = size
        self.blend = blend
        self.emit = True
        self._accum = 0.0            # for sub-1 rates

    def update(self):
        """Spawn particles for this frame and tick the emitter."""
        if not self.emit:
            return
        self._accum += self.rate
        n = int(self._accum)
        self._accum -= n
        for _ in range(n):
            life = self.life * (1.0 + random.uniform(-self.life_var,
                                                     self.life_var))
            vx = self.vx + random.uniform(-self.vx_var, self.vx_var)
            vy = self.vy + random.uniform(-self.vy_var, self.vy_var)
            if self.color_list:
                color = random.choice(self.color_list)
            else:
                color = self.color
            particle(self.x, self.y, vx, vy,
                     life=max(1, int(life)),
                     color=color,
                     size=self.size,
                     ax=self.ax, ay=self.ay,
                     drag=self.drag, blend=self.blend)

# ======================================================================
# PRESETS (one-line convenience for common effects)
# ======================================================================

def burst_explosion(x, y, color=8):
    """Big radial burst with additive blending - looks like an explosion."""
    burst(x, y, count=40, color=color, life=20, speed=3.0,
          size=2, drag=0.92, blend="add", speed_var=0.6)
    # Inner flash: brighter, smaller, shorter
    burst(x, y, count=15, color=10, life=10, speed=1.5,
          size=3, drag=0.85, blend="add", speed_var=0.5)

def burst_sparks(x, y, color=10, direction=0):
    """Small, fast, gravity-affected spark spray.

    direction: where the sparks come from (radians). Use 0 for upward
               from the floor, math.pi for downward, etc.
    """
    burst(x, y, count=12, color=color, life=25, speed=2.5,
          size=1, ay=0.15, drag=0.98,
          spread_angle=math.pi * 0.6,
          base_angle=-math.pi/2 + direction,
          blend="add", speed_var=0.4)

def burst_smoke(x, y, color=5, count=8):
    """Slow, rising, fading puff of smoke."""
    burst(x, y, count=count, color=color, life=60, speed=0.5,
          size=2, ay=-0.05, drag=0.95,
          blend="alpha", speed_var=0.5, life_var=0.3)

def burst_confetti(x, y, count=30):
    """Colorful particles falling from the spawn point."""
    colors = [8, 9, 10, 11, 12, 14]
    for _ in range(count):
        c = random.choice(colors)
        burst(x, y, count=1, color=c, life=80, speed=1.5,
              size=1, ay=0.08, drag=0.99,
              spread_angle=math.pi, base_angle=-math.pi/2,
              speed_var=0.6, life_var=0.4)
