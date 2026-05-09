"""
py16.samples
=============
Sample playback. Adds .ogg/.wav samples as a 5th waveform alongside
the synthesized ones (square/triangle/saw/noise).

A cart holds up to 16 sample slots. Each slot stores:
- the raw OGG/WAV bytes (base64-encoded in the cart JSON)
- a base note (the pitch at which the sample plays unaltered)
- a name (for display in editors)

Playing a sample at a different note resamples it: higher notes shorten
the playback (sound higher), lower notes stretch it. Standard sampler
behavior.

API:
    py16.load_sample(slot, path)        Load an audio file into a slot
    py16.play_sample(slot, note=NOTE_C3) Play a sample at the given note
    py16.set_sample_name(slot, name)
    py16.set_sample_base_note(slot, note)
"""

import os
import io
import base64
import struct
import wave
import pygame

from . import state

NUM_SAMPLES = 16
MAX_SAMPLE_BYTES = 256 * 1024   # per slot, before base64 encoding

# WAVE constant: must match audio.py's WAVE_NOISE+1 etc.
# We add this as the "sample" instrument.
WAVE_SAMPLE = 4

# Default base note: C-4 (MIDI 60)
DEFAULT_BASE_NOTE = 24   # in py-16 note numbering (C-3 = 24, see sfx_data)

# ----------------------------------------------------------------------
# DATA
# ----------------------------------------------------------------------

def make_empty_sample_slot():
    """Returns a fresh empty sample slot."""
    return {
        "name":      "",         # display name
        "data":      None,       # base64 string of OGG/WAV bytes, or None
        "format":    None,       # "ogg" or "wav"
        "base_note": DEFAULT_BASE_NOTE,
        "_pcm":      None,       # decoded PCM cache (mono 16-bit) - not in cart
        "_sr":       0,          # sample rate of decoded PCM
    }

def init_state():
    """Called by core._init_engine()."""
    if not hasattr(state, "samples"):
        state.samples = [make_empty_sample_slot() for _ in range(NUM_SAMPLES)]
    if not hasattr(state, "sample_play_cache"):
        state.sample_play_cache = {}   # cache of pitch-shifted Sounds

# ----------------------------------------------------------------------
# LOADING
# ----------------------------------------------------------------------

def load_sample(slot, path, base_note=None, name=None):
    """Loads an audio file into a sample slot. Supports .ogg and .wav.

    The file is read into memory, decoded to PCM for playback, and
    stored as base64 inside the cart. Max 256 KB per slot.
    """
    if slot < 0 or slot >= NUM_SAMPLES:
        raise ValueError(f"slot must be 0..{NUM_SAMPLES - 1}")
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    ext = os.path.splitext(path)[1].lower()
    if ext not in (".ogg", ".wav"):
        raise ValueError(f"Unsupported format: {ext} (use .ogg or .wav)")

    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) > MAX_SAMPLE_BYTES:
        raise ValueError(
            f"Sample too large: {len(raw)//1024} KB > "
            f"{MAX_SAMPLE_BYTES//1024} KB. Try a shorter or "
            f"lower-bitrate file."
        )

    init_state()
    s = state.samples[slot]
    s["data"] = base64.b64encode(raw).decode("ascii")
    s["format"] = ext[1:]    # "ogg" or "wav"
    if base_note is not None:
        s["base_note"] = base_note
    if name is not None:
        s["name"] = name
    elif not s["name"]:
        s["name"] = os.path.splitext(os.path.basename(path))[0][:16].upper()

    # Decode to PCM and cache
    _decode_to_pcm(slot)
    # Invalidate any pitch-shifted versions
    _purge_play_cache(slot)
    return s

def clear_sample(slot):
    init_state()
    state.samples[slot] = make_empty_sample_slot()
    _purge_play_cache(slot)

def set_sample_name(slot, name):
    init_state()
    state.samples[slot]["name"] = name[:16]

def set_sample_base_note(slot, note):
    init_state()
    state.samples[slot]["base_note"] = int(note)
    _purge_play_cache(slot)

# ----------------------------------------------------------------------
# PCM DECODE
# ----------------------------------------------------------------------

def _decode_to_pcm(slot):
    """Decodes the slot's raw audio bytes into mono 16-bit PCM samples
    plus the sample rate. Result cached on the slot dict.

    Strategy: load via pygame.mixer.Sound, then read its raw buffer.
    pygame returns bytes in the mixer's format (44100, -16, 2 stereo).
    We mix down to mono.
    """
    init_state()
    s = state.samples[slot]
    if not s["data"]:
        s["_pcm"] = None
        s["_sr"] = 0
        return

    raw = base64.b64decode(s["data"])
    try:
        sound = pygame.mixer.Sound(io.BytesIO(raw))
    except Exception as e:
        print(f"Sample slot {slot} decode failed: {e}")
        s["_pcm"] = None
        s["_sr"] = 0
        return

    pcm_bytes = sound.get_raw()
    mixer_init = pygame.mixer.get_init() or (44100, -16, 2)
    sr, _bits, channels = mixer_init

    # Convert to mono int16 list
    if channels == 2:
        # Each sample is 4 bytes (2x int16). Mix down to mono.
        n = len(pcm_bytes) // 4
        samples = [0] * n
        for i in range(n):
            l, r = struct.unpack_from('<hh', pcm_bytes, i * 4)
            samples[i] = (l + r) // 2
    else:
        n = len(pcm_bytes) // 2
        samples = list(struct.unpack(f'<{n}h', pcm_bytes))

    s["_pcm"] = samples
    s["_sr"] = sr

def _purge_play_cache(slot):
    """Drop pitch-shifted sound cache entries for this slot."""
    if not hasattr(state, "sample_play_cache"):
        return
    keys = [k for k in state.sample_play_cache if k[0] == slot]
    for k in keys:
        del state.sample_play_cache[k]

# ----------------------------------------------------------------------
# PLAYBACK
# ----------------------------------------------------------------------

def play_sample(slot, note=None, channel=-1, volume=1.0):
    """Plays a sample at the given py-16 note number.

    note=None: play at the slot's base_note (no pitch shift)
    """
    init_state()
    if not state.sound_enabled:
        return
    if slot < 0 or slot >= NUM_SAMPLES:
        return
    s = state.samples[slot]
    if not s["_pcm"]:
        return

    if note is None:
        note = s["base_note"]

    # Pitch ratio = 2^((note - base) / 12)
    semitones = note - s["base_note"]
    ratio = 2.0 ** (semitones / 12.0)

    # Cache pitch-shifted Sound objects (creating one is ~ms-expensive)
    key = (slot, int(round(semitones * 100)))   # 100 buckets per semitone
    if key not in state.sample_play_cache:
        state.sample_play_cache[key] = _build_shifted_sound(s, ratio)
    sound = state.sample_play_cache[key]
    if sound is None:
        return

    sound.set_volume(0.4 * volume)
    if channel < 0:
        sound.play()
    else:
        ch = pygame.mixer.Channel(channel % 8)
        ch.play(sound)

def _build_shifted_sound(slot_data, ratio):
    """Resample slot_data['_pcm'] by 1/ratio and return a pygame.Sound.
    Higher ratio = higher pitch = shorter Sound."""
    pcm = slot_data["_pcm"]
    sr = slot_data["_sr"]
    if not pcm or sr <= 0:
        return None

    # Output length: shorter when ratio > 1 (higher pitch)
    n_in = len(pcm)
    n_out = max(1, int(n_in / ratio))

    # Linear interpolation resample
    out = bytearray(n_out * 2)
    for i in range(n_out):
        src_pos = i * ratio
        idx = int(src_pos)
        frac = src_pos - idx
        if idx + 1 < n_in:
            v = int(pcm[idx] * (1 - frac) + pcm[idx + 1] * frac)
        else:
            v = pcm[idx] if idx < n_in else 0
        # Clamp
        if v >  32767: v =  32767
        if v < -32768: v = -32768
        struct.pack_into('<h', out, i * 2, v)

    # Build Sound. pygame mixer is stereo-int16 - if so, duplicate to stereo.
    mixer_init = pygame.mixer.get_init() or (44100, -16, 2)
    _, _, channels = mixer_init
    if channels == 2:
        # Duplicate mono to stereo
        stereo = bytearray(n_out * 4)
        for i in range(n_out):
            sample = struct.unpack_from('<h', out, i * 2)[0]
            struct.pack_into('<hh', stereo, i * 4, sample, sample)
        return pygame.mixer.Sound(buffer=bytes(stereo))
    return pygame.mixer.Sound(buffer=bytes(out))

# ----------------------------------------------------------------------
# CART SAVE/LOAD INTEGRATION
# ----------------------------------------------------------------------

def serialize_for_cart():
    """Returns list of slot dicts suitable for cart JSON."""
    init_state()
    out = []
    for s in state.samples:
        out.append({
            "name":      s["name"],
            "data":      s["data"],
            "format":    s["format"],
            "base_note": s["base_note"],
        })
    return out

def restore_from_cart(slots_data):
    """Restore samples from cart JSON. Triggers PCM decode for each."""
    init_state()
    if not slots_data:
        return
    for i, sd in enumerate(slots_data):
        if i >= NUM_SAMPLES:
            break
        slot = state.samples[i]
        slot["name"]      = sd.get("name", "")
        slot["data"]      = sd.get("data", None)
        slot["format"]    = sd.get("format", None)
        slot["base_note"] = sd.get("base_note", DEFAULT_BASE_NOTE)
        # Decode to PCM if we have data
        if slot["data"]:
            _decode_to_pcm(i)
    state.sample_play_cache = {}
