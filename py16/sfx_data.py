"""
py16.sfx_data
=============
data structures for SFX-Patches and Music-Patterns.

DATENMODELL
-----------

SFX-PATCH:
    32 Notencelln, jede cell = (note, instrument, volume, effect)
        note       : 0..63   (Halbtonsteps, 0 = C0, 24 = C2, 36 = C3, etc.)
                              value 255 = Pause/leer
        instrument : 0..7    (siehe INSTRUMENTS)
        volume     : 0..7    (0 = stumm, 7 = max)
        effect     : 0..7    (siehe EFFECTS)
    Plus Header:
        speed      : 1..32   (Frames pro Notencell, niedriger = schneller)
        loop_start : 0..31   (loop start, 0 if kein Loop)
        loop_end   : 0..32   (loop end exclusive, 0 if no loop)

MUSIC-PATTERN:
    4 SFX-IDs (for 4 parallel channels)
        value 0..63 = SFX-Slot, 255 = empty channel
    Plus Flags:
        loop  : True/False  (am Pattern-Ende back zum Anfang)
        stop  : True/False  (am Pattern-Ende Musik anhalten)

MUSIC-TRACK (vereinfacht):
    Sequenz von Pattern-IDs, die nacheinander geplays werden.
    Track-Ende: back zum Anfang (sofern kein "stop" Pattern).
"""

# ----------------------------------------------------------------------
# KONSTANTEN
# ----------------------------------------------------------------------

NUM_SFX           = 64    # 64 SFX-Slots
NUM_PATTERNS      = 64    # 64 Music-Patterns
NUM_TRACKS        = 8     # 8 Tracks (Music-Songs)
NOTES_PER_SFX     = 32    # 32 Notencelln pro SFX
CHANNELS_PER_PAT  = 4     # 4 parallel channels pro Pattern

NOTE_EMPTY = 255          # Marker for empty Note
SFX_EMPTY  = 255          # marker for empty pattern channel

# Instrumente (maps auf waveforms + Modulationen)
INST_SQUARE   = 0
INST_TRIANGLE = 1
INST_SAW      = 2
INST_NOISE    = 3
INST_TILTED   = 4   # Square with ungewoehnlichem Duty-Cycle
INST_ORGAN    = 5   # Triangle + Square gemischt
INST_PHASER   = 6   # Saw with Pitch-Wobble
INST_BRASS    = 7   # Saw with kurzem Attack

# Samples 0..15 sind als Instrumente 8..23 nutzbar
INST_SAMPLE_FIRST = 8
INST_SAMPLE_LAST  = 23

def is_sample_instrument(inst):
    """Returns True if `inst` references a sample slot rather than synth."""
    return INST_SAMPLE_FIRST <= inst <= INST_SAMPLE_LAST

def instrument_to_sample_slot(inst):
    """Maps an instrument number to the sample slot (0..15)."""
    return inst - INST_SAMPLE_FIRST

INSTRUMENT_NAMES = ["SQR", "TRI", "SAW", "NSE", "TLT", "ORG", "PHA", "BRS"]

# Effekte
FX_NONE      = 0
FX_SLIDE     = 1   # pitch gleitet von vorheriger Note zu currentr
FX_VIBRATO   = 2   # pitchn-Modulation
FX_DROP      = 3   # pitch faellt during der Note
FX_FADE_IN   = 4   # volume steigt
FX_FADE_OUT  = 5   # volume faellt
FX_ARP_FAST  = 6   # Schnelles Akkord-Arpeggio
FX_ARP_SLOW  = 7   # Langsames Akkord-Arpeggio

EFFECT_NAMES = ["---", "SLD", "VIB", "DRP", "FIN", "FOT", "ARF", "ARS"]

# frequency-Tabelle: Note 0 = C0 (~16.35 Hz)
# 12 Halbtoene pro Oktave, 5 Oktaven = 60 Notenslots, wir nutzen 64 als Puffer
def note_freq(note):
    """Returns frequency in Hz for eine MIDI-like Note (0..63)."""
    if note == NOTE_EMPTY or note < 0:
        return 0
    # Note 0 = C0, also 16.351597 Hz; 12 Halbtoene pro Oktave
    return 16.351597 * (2 ** (note / 12.0))

# note names for display
_NOTE_LETTERS = ["C-", "C#", "D-", "D#", "E-", "F-",
                 "F#", "G-", "G#", "A-", "A#", "B-"]

def note_name(note):
    """'C-3', 'F#4', '---' for leer."""
    if note == NOTE_EMPTY:
        return "---"
    octave = note // 12
    semi = note % 12
    return f"{_NOTE_LETTERS[semi]}{octave}"

# ----------------------------------------------------------------------
# DATENINSTANZEN (default leer)
# ----------------------------------------------------------------------

def make_empty_sfx():
    """Creates an empty SFX patch."""
    return {
        "speed": 8,           # default: ~7.5 notes/sec at 60 FPS
        "loop_start": 0,
        "loop_end": 0,
        # ADSR envelope in milliseconds (attack/decay/release)
        # and sustain level 0.0..1.0. default: fast attack, immediate sustain
        # at full volume, no release - sounds like old SFX engine
        "attack_ms":  0,      # 0..200ms
        "decay_ms":   0,      # 0..500ms
        "sustain":    1.0,    # 0.0..1.0 (amp ratio after decay)
        "release_ms": 0,      # 0..500ms
        # Pulse width for square wave (only relevant for INST_SQUARE+INST_TILTED)
        # 0.125 = 12.5%, 0.25 = 25%, 0.5 = 50% (default), 0.75 = 75%
        "pulse_width": 0.5,
        "notes": [
            (NOTE_EMPTY, 0, 0, FX_NONE) for _ in range(NOTES_PER_SFX)
        ],
    }

def make_empty_pattern():
    """Creates an empty music pattern."""
    return {
        "channels": [SFX_EMPTY] * CHANNELS_PER_PAT,
        "loop": False,
        "stop": False,
    }

def make_empty_track():
    """Liste von Pattern-IDs."""
    return []
