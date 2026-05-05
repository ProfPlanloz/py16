"""
py16.audio
==========
Sound engine with 4 waveforms (Square, Triangle, Saw, Noise),
sound cache and 8 mixer channels.
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

def _build_sound(pitch, duration_ms, wave,
                 pulse_width=0.5,
                 attack_ms=0, decay_ms=0, sustain=1.0, release_ms=0):
    """Creates a pygame.Sound with given frequency, waveform
    and ADSR envelope.

    pulse_width : only relevant for WAVE_SQUARE. 0.0..1.0 (high-phase ratio)
    attack_ms   : time from 0 to full volume
    decay_ms    : time from full to sustain level
    sustain     : volume level (0.0..1.0) during sustain phase
    release_ms  : time from sustain to 0 at the end of the note

    If all ADSR times are 0 and sustain=1.0, the envelope is
    flat (old sound).
    """
    sr = 44100
    n = max(1, int(sr * (duration_ms / 1000.0)))
    period = max(2, int(sr / pitch)) if pitch > 0 else 2
    amp = 8000
    buf = bytearray(n * 2)

    # 1) Generate waveform samples (without volume)
    samples = _generate_waveform(wave, n, period, pitch, duration_ms,
                                 pulse_width)

    # 2) Compute ADSR envelope (multiplier per sample)
    flat_envelope = (attack_ms == 0 and decay_ms == 0
                     and release_ms == 0 and sustain >= 1.0)

    if flat_envelope:
        # Fast path: no envelope, simply apply amp
        for i in range(n):
            struct.pack_into('<h', buf, i * 2, int(samples[i] * amp))
    else:
        attack_n  = max(1, int(sr * attack_ms / 1000.0)) if attack_ms > 0 else 0
        decay_n   = int(sr * decay_ms / 1000.0)
        release_n = int(sr * release_ms / 1000.0)
        # Sustain runs from end(Decay) to start(Release)
        sustain_start = attack_n + decay_n
        release_start = max(sustain_start, n - release_n)

        for i in range(n):
            if i < attack_n:
                env = i / attack_n   # linear rise 0->1
            elif i < sustain_start:
                # Decay: 1 -> sustain
                progress = (i - attack_n) / max(1, decay_n)
                env = 1.0 - (1.0 - sustain) * progress
            elif i < release_start:
                env = sustain
            else:
                # Release: sustain -> 0
                progress = (i - release_start) / max(1, release_n)
                env = sustain * (1.0 - progress)
            v = int(samples[i] * amp * env)
            # Clamp to prevent overflow
            if v >  32767: v =  32767
            if v < -32768: v = -32768
            struct.pack_into('<h', buf, i * 2, v)

    s = pygame.mixer.Sound(buffer=bytes(buf))
    s.set_volume(0.2)
    return s

def _generate_waveform(wave, n, period, pitch, duration_ms, pulse_width):
    """Generates n normalized samples (-1..1) of the given waveform.
    Volume and envelope are applied by the caller."""
    out = [0.0] * n

    if wave == WAVE_SQUARE:
        # Pulse-width: high_n samples high, then period-high_n samples low
        high_n = max(1, int(period * pulse_width))
        for i in range(n):
            phase_pos = i % period
            out[i] = 1.0 if phase_pos < high_n else -1.0
    elif wave == WAVE_TRIANGLE:
        for i in range(n):
            phase = (i % period) / period
            out[i] = 4 * abs(phase - 0.5) - 1
    elif wave == WAVE_SAW:
        for i in range(n):
            phase = (i % period) / period
            out[i] = phase * 2 - 1
    elif wave == WAVE_NOISE:
        rng = random.Random(42 + pitch + duration_ms)
        hold = max(1, period // 4)
        cur = 0
        for i in range(n):
            if i % hold == 0:
                cur = rng.uniform(-1.0, 1.0)
            out[i] = cur

    return out

# ======================================================================
# OEFFENTLICHE API
# ======================================================================

def tone(pitch, duration_ms=100, wave=WAVE_SQUARE, channel=-1,
         pulse_width=0.5,
         attack_ms=0, decay_ms=0, sustain=1.0, release_ms=0):
    """
    Plays a single tone (low-level, without SFX patches).
    For patch-based sound see tracker.sfx(id) and tracker.music(id).

    pitch       : frequency in Hz
    duration_ms : length in milliseconds
    wave        : WAVE_SQUARE | WAVE_TRIANGLE | WAVE_SAW | WAVE_NOISE
    channel     : -1 = free channel, else 0..7
    pulse_width : only for WAVE_SQUARE (0.0..1.0, default 0.5)
    attack_ms   : envelope attack time in ms (default 0)
    decay_ms    : envelope decay time in ms
    sustain     : sustain level 0.0..1.0 (default 1.0 = full)
    release_ms  : release time at note end in ms
    """
    if not state.sound_enabled or pitch <= 0:
        return
    # Cache key includes all sound parameters so different
    # variants don't collide
    key = (int(pitch), int(duration_ms), wave,
           round(pulse_width, 3),
           attack_ms, decay_ms, round(sustain, 3), release_ms)
    if key not in state.sfx_cache:
        state.sfx_cache[key] = _build_sound(
            pitch, duration_ms, wave,
            pulse_width=pulse_width,
            attack_ms=attack_ms, decay_ms=decay_ms,
            sustain=sustain, release_ms=release_ms,
        )
    sound = state.sfx_cache[key]
    if channel < 0:
        sound.play()
    else:
        ch = pygame.mixer.Channel(channel % 8)
        ch.play(sound)
