"""
py16.state
==========
Zentraler, mutabler Zustand der Engine. Alle Module greifen auf diese
Variablen ueber `from py16 import state` and `state.<name>` zu.
Das stellt sicher, dass alle Module dieselbe Instanz sehen.
"""

# ----------------------------------------------------------------------
# Pygame-Surfaces and Clock
# ----------------------------------------------------------------------
screen        = None    # 256x224 Logik-Surface
sprite_sheet  = None    # 256x256 Sprite-Sheet
clock         = None    # pygame.time.Clock
sound_enabled = False

# ----------------------------------------------------------------------
# input
# ----------------------------------------------------------------------
keys          = {}
keys_prev     = {}

mouse_x       = 0
mouse_y       = 0
mouse_btn     = [False, False, False]
mouse_btn_prev = [False, False, False]

# ----------------------------------------------------------------------
# Kamera & Clipping
# ----------------------------------------------------------------------
cam_x         = 0
cam_y         = 0
clip_rect     = None
frame_count   = 0
blend_mode    = "normal"   # "normal" | "add" | "sub" | "alpha"
blend_alpha   = 128        # 0..255, used when blend_mode == "alpha"

# ----------------------------------------------------------------------
# Map and Sprite-Flags
# Werden in core._init_engine() initialisiert, weil constants dort wohnen
# ----------------------------------------------------------------------
map_data      = None    # Liste von Listen, [MAP_H][MAP_W]
sprite_flags  = None    # Liste with 1024 Eintraegen

# ----------------------------------------------------------------------
# Caches
# ----------------------------------------------------------------------
font_cache    = {}      # (char, color_idx) -> Surface
sfx_cache     = {}      # (pitch, dur, wave) -> Sound

# ----------------------------------------------------------------------
# Palette-Remap (for pal()) and Transparenz-Set (for palt())
# ----------------------------------------------------------------------
pal_remap     = list(range(256))
transparent   = {0}

# ----------------------------------------------------------------------
# Editor-State
# ----------------------------------------------------------------------
editor_mode       = None    # None | "sprite" | "map"
edit_sprite       = 1
edit_color        = 7
edit_tile         = 1
edit_map_cam      = [0, 0]
edit_map_layer    = 0       # active map layer in editor (0..3)
edit_picker_page  = 0
