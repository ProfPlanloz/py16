"""
py16.controller
================
Gamepad / joystick support, with multi-player slot management.

Up to 4 players, each with their own controller. The first connected
controller becomes Player 1, the second becomes Player 2, etc.

Logical button names match the keyboard ones:
  'left', 'right', 'up', 'down'   -> D-Pad + left analog stick
  'z'                             -> south face button (A on Xbox)
  'x'                             -> east face button (B on Xbox)
  'a'                             -> west face button (X on Xbox)
  's'                             -> north face button (Y on Xbox)
  'enter'                         -> Start
  'space'                         -> Back / Select
  'shift'                         -> shoulder button (LB)

Player identification:
  player=0 (default)  : input from ANY source (keyboard + all gamepads)
  player=1            : keyboard if no gamepads connected, else gamepad #1
  player=2..4         : gamepad #2..4 only (no keyboard share)

Hot-plug is supported: connecting/disconnecting controllers mid-game
just works. Disconnected players' slots stay empty (their cart can
detect this via py16.player_connected(N)) so the game can pause until
they reconnect.

Internally uses pygame's higher-level Controller API when available
(consults SDL's gamepad mapping database for hundreds of devices),
falls back to raw Joystick for exotic devices.
"""

import pygame

from . import state

# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------

# Maximum simultaneous players. SNES had 2 by default, 4 with multitap.
MAX_PLAYERS = 4

# Analog stick deadzone: ignore tiny drift around center.
DEADZONE = 0.30

def _controller_btn_map():
    """Mapping from logical button name to SDL CONTROLLER_BUTTON_* constants.
    Resolved lazily so import doesn't fail on older pygame."""
    try:
        return {
            'z':     pygame.CONTROLLER_BUTTON_A,
            'x':     pygame.CONTROLLER_BUTTON_B,
            'a':     pygame.CONTROLLER_BUTTON_X,
            's':     pygame.CONTROLLER_BUTTON_Y,
            'enter': pygame.CONTROLLER_BUTTON_START,
            'space': pygame.CONTROLLER_BUTTON_BACK,
            'shift': pygame.CONTROLLER_BUTTON_LEFTSHOULDER,
            'up':    pygame.CONTROLLER_BUTTON_DPAD_UP,
            'down':  pygame.CONTROLLER_BUTTON_DPAD_DOWN,
            'left':  pygame.CONTROLLER_BUTTON_DPAD_LEFT,
            'right': pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
        }
    except AttributeError:
        return {}

# Fallback for raw joystick (no SDL gamepad mapping available).
RAW_JOY_BUTTON_MAP = {
    'z':     0,   # bottom face button
    'x':     1,   # right face button
    'a':     2,   # left face button
    's':     3,   # top face button
    'shift': 4,   # left shoulder
    'space': 6,   # back/select
    'enter': 7,   # start
}

# ----------------------------------------------------------------------
# STATE
# ----------------------------------------------------------------------

def _ensure_state():
    """Initialise gamepad-related state if not yet done."""
    if not hasattr(state, "controllers"):
        state.controllers = {}            # instance_id -> Controller or Joystick
        state.controller_is_gamepad = {}  # instance_id -> bool
        state.controller_to_player  = {}  # instance_id -> player slot 1..MAX_PLAYERS
        # Per-player button state (set of held logical buttons)
        state.player_btn_state      = [set() for _ in range(MAX_PLAYERS)]
        state.player_btn_state_prev = [set() for _ in range(MAX_PLAYERS)]
        # Combined "any source" state (kept for back-compat: player=0 case)
        state.gamepad_btn_state      = set()
        state.gamepad_btn_state_prev = set()

def init():
    """Called once at engine start. Initialises pygame.joystick and
    attaches all already-connected controllers."""
    _ensure_state()
    try:
        pygame.joystick.init()
    except pygame.error as e:
        print(f"Joystick init failed: {e}")
        return

    for i in range(pygame.joystick.get_count()):
        _attach_device(i)

# ----------------------------------------------------------------------
# DEVICE MANAGEMENT
# ----------------------------------------------------------------------

def _next_free_player_slot():
    """Find the lowest free player slot (1..MAX_PLAYERS), or None if full."""
    used = set(state.controller_to_player.values())
    for slot in range(1, MAX_PLAYERS + 1):
        if slot not in used:
            return slot
    return None

def _attach_device(device_index):
    """Attach the device at the given pygame device_index. Prefers the
    Controller (gamepad) API if the device is recognised; falls back to
    raw Joystick if not."""
    _ensure_state()
    instance_id = None
    ctrl = None
    is_gamepad = False

    try:
        if hasattr(pygame, "Controller") and pygame.controller.is_controller(device_index):
            ctrl = pygame.Controller(device_index)
            instance_id = ctrl.get_instance_id()
            is_gamepad = True
    except (pygame.error, AttributeError):
        ctrl = None

    if ctrl is None:
        try:
            ctrl = pygame.joystick.Joystick(device_index)
            ctrl.init()
            instance_id = ctrl.get_instance_id()
        except pygame.error as e:
            print(f"Could not attach device {device_index}: {e}")
            return

    state.controllers[instance_id] = ctrl
    state.controller_is_gamepad[instance_id] = is_gamepad

    # Assign to the lowest free player slot
    slot = _next_free_player_slot()
    if slot is not None:
        state.controller_to_player[instance_id] = slot
        try:
            name = ctrl.get_name()
        except Exception:
            name = "controller"
        kind = "gamepad" if is_gamepad else "joystick"
        print(f"P{slot} connected: {name} ({kind}, id {instance_id})")
    else:
        print(f"All {MAX_PLAYERS} player slots full, ignoring extra controller")

def _detach_device(instance_id):
    _ensure_state()
    if instance_id in state.controllers:
        ctrl = state.controllers.pop(instance_id)
        state.controller_is_gamepad.pop(instance_id, None)
        slot = state.controller_to_player.pop(instance_id, None)
        try:
            ctrl.quit()
        except Exception:
            pass
        if slot is not None:
            # Clear that player's button state
            if 1 <= slot <= MAX_PLAYERS:
                state.player_btn_state[slot - 1].clear()
                state.player_btn_state_prev[slot - 1].clear()
            print(f"P{slot} disconnected (id {instance_id})")
        else:
            print(f"Controller disconnected (id {instance_id})")

def handle_event(event):
    """Process a pygame event for gamepad hot-plug. Called from the main
    loop's event dispatch."""
    if event.type == pygame.JOYDEVICEADDED:
        _attach_device(event.device_index)
    elif event.type == pygame.JOYDEVICEREMOVED:
        _detach_device(event.instance_id)

# ----------------------------------------------------------------------
# POLLING (called once per frame)
# ----------------------------------------------------------------------

def update():
    """Poll all attached controllers and rebuild per-player button state.
    Called once per frame from the main loop, before cart update()."""
    _ensure_state()

    # Save previous state for edge detection
    state.gamepad_btn_state_prev = state.gamepad_btn_state
    for i in range(MAX_PLAYERS):
        state.player_btn_state_prev[i] = state.player_btn_state[i]

    # Clear current state
    state.gamepad_btn_state = set()
    state.player_btn_state = [set() for _ in range(MAX_PLAYERS)]

    # Poll each controller into its player's slot
    for inst_id, ctrl in state.controllers.items():
        slot = state.controller_to_player.get(inst_id)
        if slot is None:
            continue
        per_player = set()
        if state.controller_is_gamepad.get(inst_id, False):
            _poll_gamepad(ctrl, per_player)
        else:
            _poll_raw_joystick(ctrl, per_player)
        # Add to that player's slot AND to the combined "any" state
        state.player_btn_state[slot - 1] |= per_player
        state.gamepad_btn_state |= per_player

def _poll_gamepad(ctrl, pressed):
    """Poll a Controller via the SDL gamepad API."""
    btn_map = _controller_btn_map()
    if not btn_map:
        return
    try:
        for logical, sdl_btn in btn_map.items():
            if ctrl.get_button(sdl_btn):
                pressed.add(logical)
    except pygame.error:
        return

    try:
        ax = ctrl.get_axis(getattr(pygame, "CONTROLLER_AXIS_LEFTX", 0))
        ay = ctrl.get_axis(getattr(pygame, "CONTROLLER_AXIS_LEFTY", 1))
        if ax < -DEADZONE: pressed.add('left')
        if ax >  DEADZONE: pressed.add('right')
        if ay < -DEADZONE: pressed.add('up')
        if ay >  DEADZONE: pressed.add('down')
    except pygame.error:
        pass

def _poll_raw_joystick(joy, pressed):
    """Poll a raw Joystick (no SDL gamepad mapping available)."""
    try:
        n_buttons = joy.get_numbuttons()
        for logical, idx in RAW_JOY_BUTTON_MAP.items():
            if idx < n_buttons and joy.get_button(idx):
                pressed.add(logical)
    except pygame.error:
        return

    try:
        if joy.get_numaxes() >= 2:
            ax = joy.get_axis(0)
            ay = joy.get_axis(1)
            if ax < -DEADZONE: pressed.add('left')
            if ax >  DEADZONE: pressed.add('right')
            if ay < -DEADZONE: pressed.add('up')
            if ay >  DEADZONE: pressed.add('down')
    except pygame.error:
        pass

    try:
        if joy.get_numhats() >= 1:
            hx, hy = joy.get_hat(0)
            if hx < 0: pressed.add('left')
            if hx > 0: pressed.add('right')
            if hy > 0: pressed.add('up')
            if hy < 0: pressed.add('down')
    except pygame.error:
        pass

# ----------------------------------------------------------------------
# QUERY (called from input.btn() / btnp())
# ----------------------------------------------------------------------

def is_held(name, player=0):
    """Returns True if the given logical button is held by the given player.

    player=0 : any source (keyboard + all gamepads). Default for back-compat.
    player=1 : Player 1's controller only. Falls back to keyboard if no
               controllers are connected (so single-player carts written
               as `btn('left', player=1)` work without a gamepad).
    player=2..4 : that player's controller only.
    """
    _ensure_state()
    if player == 0:
        return name in state.gamepad_btn_state
    if 1 <= player <= MAX_PLAYERS:
        if name in state.player_btn_state[player - 1]:
            return True
        # P1 falls back to keyboard if no gamepads are present at all
        if player == 1 and not state.controllers:
            return False  # caller (input.btn) handles keyboard separately
        return False
    return False

def was_just_pressed(name, player=0):
    _ensure_state()
    if player == 0:
        return (name in state.gamepad_btn_state
                and name not in state.gamepad_btn_state_prev)
    if 1 <= player <= MAX_PLAYERS:
        cur  = state.player_btn_state[player - 1]
        prev = state.player_btn_state_prev[player - 1]
        return name in cur and name not in prev
    return False

def num_connected():
    """Total number of controllers currently connected (regardless of slot)."""
    _ensure_state()
    return len(state.controllers)

def player_connected(player):
    """Is the given player slot occupied? player=1..MAX_PLAYERS."""
    _ensure_state()
    if not (1 <= player <= MAX_PLAYERS):
        return False
    return player in state.controller_to_player.values()

def player_count():
    """How many players have controllers assigned (1..MAX_PLAYERS)."""
    _ensure_state()
    return len(state.controller_to_player)

def names():
    """List of names of all connected controllers."""
    _ensure_state()
    out = []
    for inst_id, ctrl in state.controllers.items():
        try:
            out.append(ctrl.get_name())
        except Exception:
            out.append(f"controller#{inst_id}")
    return out

def player_name(player):
    """Returns the name of the controller assigned to that player slot,
    or None if the slot is empty."""
    _ensure_state()
    for inst_id, slot in state.controller_to_player.items():
        if slot == player:
            try:
                return state.controllers[inst_id].get_name()
            except Exception:
                return f"controller#{inst_id}"
    return None
