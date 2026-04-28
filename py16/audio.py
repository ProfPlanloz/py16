"""
py16.audio
==========
Sound-Engine mit 4 Wellenformen (Square, Triangle, Saw, Noise),
Sound-Cache und 8 Mixer-Kanaelen.
"""

import struct
import random
import pygame

from . import state

# ======================================================================
# WELLENFORM-KONSTANTEN
# ======================================================================

WAVE_SQUARE   = 0
WAVE_TRIANGLE = 1
WAVE_SAW      = 2
WAVE_NOISE    = 3

# ======================================================================
# WELLENFORM-GENERATOR
# ======================================================================

def _build_sound(pitch, duration_ms, wave):
    sr = 44100
    n = max(1, int(sr * (duration_ms / 1000.0)))
    period = max(2, int(sr / pitch)) if pitch > 0 else 2
    amp = 8000
    buf = bytearray(n * 2)

    if wave == WAVE_SQUARE:
        half = max(1, period // 2)
        for i in range(n):
            v = amp if (i // half) % 2 == 0 else -amp
            struct.pack_into('<h', buf, i * 2, v)
    elif wave == WAVE_TRIANGLE:
        for i in range(n):
            phase = (i % period) / period
            tri = 4 * abs(phase - 0.5) - 1
            struct.pack_into('<h', buf, i * 2, int(tri * amp))
    elif wave == WAVE_SAW:
        for i in range(n):
            phase = (i % period) / period
            v = int((phase * 2 - 1) * amp)
            struct.pack_into('<h', buf, i * 2, v)
    elif wave == WAVE_NOISE:
        rng = random.Random(42 + pitch + duration_ms)
        hold = max(1, period // 4)
        cur = 0
        for i in range(n):
            if i % hold == 0:
                cur = rng.randint(-amp, amp)
            struct.pack_into('<h', buf, i * 2, cur)

    s = pygame.mixer.Sound(buffer=bytes(buf))
    s.set_volume(0.2)
    return s

# ======================================================================
# OEFFENTLICHE API
# ======================================================================

def tone(pitch, duration_ms=100, wave=WAVE_SQUARE, channel=-1):
    """
    Spielt einen einzelnen Ton (low-level, ohne SFX-Patches).
    Fuer Patch-basierten Sound siehe tracker.sfx(id) und tracker.music(id).

    pitch       : Frequenz in Hz
    duration_ms : Laenge in Millisekunden
    wave        : WAVE_SQUARE | WAVE_TRIANGLE | WAVE_SAW | WAVE_NOISE
    channel     : -1 = freier Kanal, sonst 0..7
    """
    if not state.sound_enabled or pitch <= 0:
        return
    key = (int(pitch), int(duration_ms), wave)
    if key not in state.sfx_cache:
        state.sfx_cache[key] = _build_sound(pitch, duration_ms, wave)
    sound = state.sfx_cache[key]
    if channel < 0:
        sound.play()
    else:
        ch = pygame.mixer.Channel(channel % 8)
        ch.play(sound)
