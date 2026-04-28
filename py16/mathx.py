"""
py16.mathx
==========
Mathe-Helfer und Engine-Helfer (Frame-Counter, FPS).
'mathx' weil 'math' bereits Standardbibliothek ist.
"""

import math
import random

from . import state

def rnd(max_val=1.0): return random.uniform(0, max_val)
def flr(val):         return math.floor(val)
def ceil(val):        return math.ceil(val)
def abs_(val):        return abs(val)
def mid(a, b, c):     return sorted((a, b, c))[1]
def sin(val):         return math.sin(val)
def cos(val):         return math.cos(val)
def atan2(y, x):      return math.atan2(y, x)
def sqrt(val):        return math.sqrt(val)

def t():
    """Frames seit Start."""
    return state.frame_count

def fps():
    """Aktuelle FPS (Mittel ueber die letzten Frames)."""
    return state.clock.get_fps() if state.clock else 0
