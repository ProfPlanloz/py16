"""
py16.tracker
============
background sequencer for SFX and music. Called once per frame
ueber `tick()` called and entscheidet, welche Note auf welchem
Audio-channel gerade active sein must.

Effekte werden tickweise processes (frame-genau bei 60 FPS):
  SLIDE   : Pitch interpoliert linear von Vorgaengernote zu currentr Note
  VIBRATO : Pitch sinusfoermig moduliert um Zielnote
  DROP    : Pitch faellt linear during der Notendauer
  FIN/FOT : volume steigt/faellt linear
  ARF/ARS : Akkord-Arpeggio (Note + Quart + Quint im Switch)
"""

import math
import pygame

from . import state, sfx_data
from .audio import (_build_sound, WAVE_SQUARE, WAVE_TRIANGLE,
                    WAVE_SAW, WAVE_NOISE)

# ----------------------------------------------------------------------
# TRACKER-STATE (im state-Modul, damit alle Module dieselbe Instanz sehen)
# ----------------------------------------------------------------------

def init_tracker_state():
    """Sets initial data in state. Called from core._init_engine()."""
    if not hasattr(state, "sfx_patches"):
        state.sfx_patches = [sfx_data.make_empty_sfx() for _ in range(sfx_data.NUM_SFX)]
        state.music_patterns = [sfx_data.make_empty_pattern() for _ in range(sfx_data.NUM_PATTERNS)]
        state.music_tracks = [sfx_data.make_empty_track() for _ in range(sfx_data.NUM_TRACKS)]

        # Aktuell laufende Tracks pro Audio-channel
        # channels 0..3 = Music, 4..7 = SFX and Editor-preview
        # Jeder Eintrag: dict with sfx_id, note_pos, frame_in_note, etc.
        state.audio_channels = [None] * 8

        # Current Music-Wiedergabe
        state.music_playing = None      # dict: track, pattern_idx, ...
        # Cache for kurze Note-Sounds
        state.note_sound_cache = {}

# ----------------------------------------------------------------------
# WELLENFORM-AUSWAHL PRO INSTRUMENT
# ----------------------------------------------------------------------

def _instrument_to_wave(inst):
    """Maps Instrument auf waveform for den Sound-Builder."""
    return {
        sfx_data.INST_SQUARE:   WAVE_SQUARE,
        sfx_data.INST_TRIANGLE: WAVE_TRIANGLE,
        sfx_data.INST_SAW:      WAVE_SAW,
        sfx_data.INST_NOISE:    WAVE_NOISE,
        sfx_data.INST_TILTED:   WAVE_SQUARE,    # Variation: different volume envelope
        sfx_data.INST_ORGAN:    WAVE_TRIANGLE,
        sfx_data.INST_PHASER:   WAVE_SAW,
        sfx_data.INST_BRASS:    WAVE_SAW,
    }.get(inst, WAVE_SQUARE)

# ----------------------------------------------------------------------
# NOTE ABSPIELEN (low level)
# ----------------------------------------------------------------------

def _play_note_on_channel(channel_idx, freq, instrument, volume_8, duration_ms,
                          patch=None, note_num=None):
    """Plays a note on a specific mixer channel.

    patch (optional): SFX patch dict with ADSR and pulse-width settings.
                      None = old flat-sound logic.
    note_num (optional): py-16 note number, needed for sample pitch shift.
                         Synth notes don't need this (they use freq)."""
    if not state.sound_enabled or freq <= 0 or volume_8 <= 0:
        return

    # Sample instrument? Dispatch to sample player instead of synth.
    if sfx_data.is_sample_instrument(instrument):
        slot = sfx_data.instrument_to_sample_slot(instrument)
        from . import samples
        samples.play_sample(slot, note=note_num,
                            channel=channel_idx,
                            volume=volume_8 / 7.0)
        return

    wave = _instrument_to_wave(instrument)

    # Extract patch settings (or defaults if none given)
    pw     = (patch or {}).get("pulse_width", 0.5)
    att_ms = (patch or {}).get("attack_ms",   0)
    dec_ms = (patch or {}).get("decay_ms",    0)
    sus    = (patch or {}).get("sustain",     1.0)
    rel_ms = (patch or {}).get("release_ms",  0)

    # Cache key incl. sound params (rounded, else cache explodes)
    key = (int(freq // 2) * 2,
           int(duration_ms // 5) * 5,
           wave,
           round(pw, 2),
           int(att_ms),
           int(dec_ms),
           round(sus, 2),
           int(rel_ms))
    if key not in state.note_sound_cache:
        sound = _build_sound(
            key[0] if key[0] > 0 else 1,
            key[1] if key[1] > 0 else 5,
            wave,
            pulse_width=pw,
            attack_ms=att_ms, decay_ms=dec_ms,
            sustain=sus, release_ms=rel_ms,
        )
        state.note_sound_cache[key] = sound
    sound = state.note_sound_cache[key]
    sound.set_volume(0.2 * (volume_8 / 7.0))
    ch = pygame.mixer.Channel(channel_idx % 8)
    ch.play(sound)

# ----------------------------------------------------------------------
# CHANNEL-RUNNER (plays einen SFX-Patch ab)
# ----------------------------------------------------------------------

def _start_sfx_on_channel(channel_idx, sfx_id, is_music=False):
    """Belegt einen Audio-channel with einem SFX-Patch."""
    if sfx_id == sfx_data.SFX_EMPTY:
        state.audio_channels[channel_idx] = None
        return
    state.audio_channels[channel_idx] = {
        "sfx_id":         sfx_id,
        "note_pos":       0,        # current Notencell 0..31
        "frame_in_note":  0,        # Frame inside der current Note
        "is_music":       is_music, # ob aus Music-Loop kommend
        "current_note":   None,     # gerade gehaltene Note
        "prev_note_value": sfx_data.NOTE_EMPTY,  # for SLIDE effect
    }

def _advance_channel(channel_idx):
    """Processes einen Frame for einen Audio-channel. Return True if fertig."""
    ch = state.audio_channels[channel_idx]
    if ch is None:
        return False

    sfx = state.sfx_patches[ch["sfx_id"]]
    speed = max(1, sfx["speed"])

    # If am Anfang einer Notencell: gamee Note an
    if ch["frame_in_note"] == 0:
        cell = sfx["notes"][ch["note_pos"]]
        note, inst, vol, fx = cell
        ch["current_note"] = cell
        if note != sfx_data.NOTE_EMPTY and vol > 0:
            # Notendauer in ms berechnen (speed * frames * (1000/60))
            dur_ms = int(speed * (1000 / 60))
            base_freq = sfx_data.note_freq(note)
            # Effekte can frequency/volume later modifizieren,
            # darum gameen wir bei FX einen kuerzeren "Tick" and retriggern
            if fx in (sfx_data.FX_VIBRATO, sfx_data.FX_DROP,
                      sfx_data.FX_SLIDE, sfx_data.FX_ARP_FAST,
                      sfx_data.FX_ARP_SLOW):
                # Fuer modulated effects: short ticks per frame
                pass  # output below in _apply_effect
            else:
                # Einfache Note: einmal angameen
                fade_vol = vol
                if fx == sfx_data.FX_FADE_IN:
                    fade_vol = max(1, vol // 2)
                _play_note_on_channel(channel_idx, base_freq, inst, fade_vol, dur_ms, patch=sfx, note_num=note)

    # Effekte tickweise apply (bei modulierten FX)
    _apply_effect(channel_idx)

    # advance frame
    ch["frame_in_note"] += 1
    if ch["frame_in_note"] >= speed:
        # Next Notencell
        ch["prev_note_value"] = ch["current_note"][0] if ch["current_note"] else sfx_data.NOTE_EMPTY
        ch["frame_in_note"] = 0
        ch["note_pos"] += 1

        # Loop-Behandlung
        loop_end = sfx["loop_end"]
        loop_start = sfx["loop_start"]
        if loop_end > loop_start and ch["note_pos"] >= loop_end:
            # Im Music-Modus loopen wir das SFX, else beenden
            if ch["is_music"]:
                ch["note_pos"] = loop_start
            else:
                state.audio_channels[channel_idx] = None
                return True

        if ch["note_pos"] >= sfx_data.NOTES_PER_SFX:
            state.audio_channels[channel_idx] = None
            return True

    return False

def _apply_effect(channel_idx):
    """Wendet Effekte tickweise an, indem kurze Note-Ticks abgefeuert werden."""
    ch = state.audio_channels[channel_idx]
    if ch is None or ch["current_note"] is None:
        return
    note, inst, vol, fx = ch["current_note"]
    if fx == sfx_data.FX_NONE or note == sfx_data.NOTE_EMPTY or vol == 0:
        return

    sfx = state.sfx_patches[ch["sfx_id"]]
    speed = sfx["speed"]
    progress = ch["frame_in_note"] / max(1, speed)   # 0..1 in der Note
    base_freq = sfx_data.note_freq(note)

    # Wir gameen pro Frame einen kurzen Tick (~16ms) with modulierter frequency/Vol.
    # Das ist not perfekt smooth, aber reicht for 16-Bit-Effekte.
    tick_ms = 30
    cur_freq = base_freq
    cur_vol = vol

    if fx == sfx_data.FX_SLIDE and ch["prev_note_value"] != sfx_data.NOTE_EMPTY:
        prev_freq = sfx_data.note_freq(ch["prev_note_value"])
        cur_freq = prev_freq + (base_freq - prev_freq) * progress
    elif fx == sfx_data.FX_VIBRATO:
        cur_freq = base_freq * (1 + 0.04 * math.sin(progress * 8 * math.pi))
    elif fx == sfx_data.FX_DROP:
        cur_freq = base_freq * (1 - 0.5 * progress)
    elif fx == sfx_data.FX_FADE_IN:
        cur_vol = max(1, int(vol * progress))
    elif fx == sfx_data.FX_FADE_OUT:
        cur_vol = max(0, int(vol * (1 - progress)))
    elif fx == sfx_data.FX_ARP_FAST:
        # Akkord: Grundton, Quart, Quint im 3-Frame-Switch
        offset = [0, 5, 7][ch["frame_in_note"] % 3]
        cur_freq = sfx_data.note_freq(note + offset)
    elif fx == sfx_data.FX_ARP_SLOW:
        offset = [0, 5, 7][(ch["frame_in_note"] // 4) % 3]
        cur_freq = sfx_data.note_freq(note + offset)

    # Bei modulierten Effekten triggern wir nur alle 2 Frames neu (else stottert es)
    if fx in (sfx_data.FX_SLIDE, sfx_data.FX_VIBRATO, sfx_data.FX_DROP,
              sfx_data.FX_ARP_FAST, sfx_data.FX_ARP_SLOW):
        if ch["frame_in_note"] % 2 == 0:
            _play_note_on_channel(channel_idx, cur_freq, inst, cur_vol, tick_ms, patch=sfx, note_num=note)
    elif fx in (sfx_data.FX_FADE_IN, sfx_data.FX_FADE_OUT):
        if ch["frame_in_note"] % 4 == 0:
            _play_note_on_channel(channel_idx, cur_freq, inst, cur_vol, tick_ms * 2, patch=sfx, note_num=note)

# ----------------------------------------------------------------------
# OEFFENTLICHE API
# ----------------------------------------------------------------------

def sfx(sfx_id, channel=-1):
    """Plays einen SFX-Patch ab. channel -1 = default (channel 4)."""
    if not state.sound_enabled:
        return
    if not (0 <= sfx_id < sfx_data.NUM_SFX):
        return
    # Standard: channel 4 for SFX, damit Music auf 0..3 ungestoert weiterlaeuft
    ch = channel if channel >= 0 else 4
    if not (0 <= ch < 8):
        return
    _start_sfx_on_channel(ch, sfx_id, is_music=False)

def music(track_id, fade_ms=0):
    """Starts a music track in the background. -1 stops music."""
    if not state.sound_enabled:
        return
    if track_id < 0:
        state.music_playing = None
        for i in range(4):     # nur Music-channels emptyn
            state.audio_channels[i] = None
        return
    if not (0 <= track_id < sfx_data.NUM_TRACKS):
        return
    track = state.music_tracks[track_id]
    if not track:
        return
    state.music_playing = {
        "track_id":      track_id,
        "pattern_seq":   0,         # Position in der Pattern-Liste des Tracks
    }
    _start_pattern(track[0])

def _start_pattern(pattern_id):
    """Belegt die 4 Music-channels with dem gegebenen Pattern."""
    if not (0 <= pattern_id < sfx_data.NUM_PATTERNS):
        return
    pat = state.music_patterns[pattern_id]
    for ch_idx in range(sfx_data.CHANNELS_PER_PAT):
        sfx_id = pat["channels"][ch_idx]
        if sfx_id != sfx_data.SFX_EMPTY:
            _start_sfx_on_channel(ch_idx, sfx_id, is_music=True)
        else:
            state.audio_channels[ch_idx] = None

def tick():
    """Called once per frame in the main loop."""
    if not state.sound_enabled:
        return

    # Alle 8 channels voranbringen (0..3 Music, 4..7 SFX/Editor)
    for i in range(8):
        _advance_channel(i)

    # Music-Pattern-Switch: nur die ersten 4 channels zaehlen for Music
    if state.music_playing:
        all_done = all(state.audio_channels[i] is None for i in range(4))
        if all_done:
            mp = state.music_playing
            track = state.music_tracks[mp["track_id"]]
            cur_pat_idx = mp["pattern_seq"]
            cur_pat = state.music_patterns[track[cur_pat_idx]] if cur_pat_idx < len(track) else None

            if cur_pat and cur_pat["stop"]:
                state.music_playing = None
                return
            if cur_pat and cur_pat["loop"]:
                _start_pattern(track[cur_pat_idx])
                return

            # Nexts Pattern in der Sequenz
            mp["pattern_seq"] += 1
            if mp["pattern_seq"] >= len(track):
                mp["pattern_seq"] = 0   # Track loopt
            _start_pattern(track[mp["pattern_seq"]])
