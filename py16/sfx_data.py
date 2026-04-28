"""
py16.sfx_data
=============
Datenstrukturen fuer SFX-Patches und Music-Patterns.

DATENMODELL
-----------

SFX-PATCH:
    32 Notenzellen, jede Zelle = (note, instrument, volume, effect)
        note       : 0..63   (Halbtonschritte, 0 = C0, 24 = C2, 36 = C3, etc.)
                              Wert 255 = Pause/leer
        instrument : 0..7    (siehe INSTRUMENTS)
        volume     : 0..7    (0 = stumm, 7 = max)
        effect     : 0..7    (siehe EFFECTS)
    Plus Header:
        speed      : 1..32   (Frames pro Notenzelle, niedriger = schneller)
        loop_start : 0..31   (Loop-Anfang, 0 wenn kein Loop)
        loop_end   : 0..32   (Loop-Ende exklusiv, 0 wenn kein Loop)

MUSIC-PATTERN:
    4 SFX-IDs (fuer 4 parallele Kanaele)
        Wert 0..63 = SFX-Slot, 255 = leerer Kanal
    Plus Flags:
        loop  : True/False  (am Pattern-Ende zurueck zum Anfang)
        stop  : True/False  (am Pattern-Ende Musik anhalten)

MUSIC-TRACK (vereinfacht):
    Sequenz von Pattern-IDs, die nacheinander gespielt werden.
    Track-Ende: zurueck zum Anfang (sofern kein "stop" Pattern).
"""

# ----------------------------------------------------------------------
# KONSTANTEN
# ----------------------------------------------------------------------

NUM_SFX           = 64    # 64 SFX-Slots
NUM_PATTERNS      = 64    # 64 Music-Patterns
NUM_TRACKS        = 8     # 8 Tracks (Music-Songs)
NOTES_PER_SFX     = 32    # 32 Notenzellen pro SFX
CHANNELS_PER_PAT  = 4     # 4 parallele Kanaele pro Pattern

NOTE_EMPTY = 255          # Marker fuer leere Note
SFX_EMPTY  = 255          # Marker fuer leeren Pattern-Kanal

# Instrumente (mappt auf Wellenformen + Modulationen)
INST_SQUARE   = 0
INST_TRIANGLE = 1
INST_SAW      = 2
INST_NOISE    = 3
INST_TILTED   = 4   # Square mit ungewoehnlichem Duty-Cycle
INST_ORGAN    = 5   # Triangle + Square gemischt
INST_PHASER   = 6   # Saw mit Pitch-Wobble
INST_BRASS    = 7   # Saw mit kurzem Attack

INSTRUMENT_NAMES = ["SQR", "TRI", "SAW", "NSE", "TLT", "ORG", "PHA", "BRS"]

# Effekte
FX_NONE      = 0
FX_SLIDE     = 1   # Tonhoehe gleitet von vorheriger Note zu aktueller
FX_VIBRATO   = 2   # Tonhoehen-Modulation
FX_DROP      = 3   # Tonhoehe faellt waehrend der Note
FX_FADE_IN   = 4   # Lautstaerke steigt
FX_FADE_OUT  = 5   # Lautstaerke faellt
FX_ARP_FAST  = 6   # Schnelles Akkord-Arpeggio
FX_ARP_SLOW  = 7   # Langsames Akkord-Arpeggio

EFFECT_NAMES = ["---", "SLD", "VIB", "DRP", "FIN", "FOT", "ARF", "ARS"]

# Frequenz-Tabelle: Note 0 = C0 (~16.35 Hz)
# 12 Halbtoene pro Oktave, 5 Oktaven = 60 Notenslots, wir nutzen 64 als Puffer
def note_freq(note):
    """Liefert Frequenz in Hz fuer eine MIDI-aehnliche Note (0..63)."""
    if note == NOTE_EMPTY or note < 0:
        return 0
    # Note 0 = C0, also 16.351597 Hz; 12 Halbtoene pro Oktave
    return 16.351597 * (2 ** (note / 12.0))

# Note-Namen fuer Anzeige
_NOTE_LETTERS = ["C-", "C#", "D-", "D#", "E-", "F-",
                 "F#", "G-", "G#", "A-", "A#", "B-"]

def note_name(note):
    """'C-3', 'F#4', '---' fuer leer."""
    if note == NOTE_EMPTY:
        return "---"
    octave = note // 12
    semi = note % 12
    return f"{_NOTE_LETTERS[semi]}{octave}"

# ----------------------------------------------------------------------
# DATENINSTANZEN (Default leer)
# ----------------------------------------------------------------------

def make_empty_sfx():
    """Erzeugt einen leeren SFX-Patch."""
    return {
        "speed": 8,           # Default: ca. 7.5 Noten/Sek bei 60 FPS
        "loop_start": 0,
        "loop_end": 0,
        "notes": [
            (NOTE_EMPTY, 0, 0, FX_NONE) for _ in range(NOTES_PER_SFX)
        ],
    }

def make_empty_pattern():
    """Erzeugt ein leeres Music-Pattern."""
    return {
        "channels": [SFX_EMPTY] * CHANNELS_PER_PAT,
        "loop": False,
        "stop": False,
    }

def make_empty_track():
    """Liste von Pattern-IDs."""
    return []
