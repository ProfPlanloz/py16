"""
py16.recording
==============
Screen recording: capture frames in memory and save as MP4 (preferred)
or animated GIF (fallback).

Usage:
  Ctrl+R          start/stop recording
  (auto-stop)     after MAX_DURATION_SEC seconds, the recording is saved
                  automatically to keep RAM usage bounded.

Files are written to ~/.py16/recordings/rec_<timestamp>.{mp4,gif}

MP4 is the default format if `imageio-ffmpeg` is installed (recommended:
pip install imageio imageio-ffmpeg). MP4 files are typically 5-10x
smaller than the equivalent GIF, with better quality, and play in any
browser/social-media platform.

If imageio-ffmpeg isn't available, falls back to GIF.

Output runs at ~30 fps (every other engine frame). MP4 is upscaled 4x
(to 1024x896) with nearest-neighbor for crisp pixels on big screens.

Override the format in your config via 'recording_format':
  'auto'  -> mp4 if available, else gif (default)
  'mp4'   -> always mp4 (errors if not available)
  'gif'   -> always gif
"""

import os
import io
import time
import pygame

from . import state

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------

# Engine runs at 60 fps - we keep every 2nd frame for ~30 fps output.
FRAME_SKIP = 2

# Bound RAM usage. Each frame at 256x224x3 bytes = 172 KB.
# At 60 sec * 30 fps = 1800 frames * 172 KB = ~300 MB max.
# That's still OK on a Pi 4 (4-8 GB) but might be tight on Pi Zero (512 MB),
# so reduce MAX_DURATION_SEC in config if you target Pi Zero.
MAX_DURATION_SEC = 60
MAX_FRAMES = MAX_DURATION_SEC * 60 // FRAME_SKIP   # ~1800

# ----------------------------------------------------------------------
# STATE
# ----------------------------------------------------------------------

def _ensure_state():
    defaults = {
        "rec_active":      False,
        "rec_frames":      None,    # list of pygame.Surface copies
        "rec_frame_count": 0,       # engine frames since rec start (for skip)
        "rec_started_at":  0.0,
        "rec_status":      "",
        "rec_status_time": 0,
        "rec_status_color": 7,
    }
    for k, v in defaults.items():
        if not hasattr(state, k):
            setattr(state, k, v)

# ----------------------------------------------------------------------
# CONTROL
# ----------------------------------------------------------------------

def is_recording():
    _ensure_state()
    return state.rec_active

def toggle():
    """Start or stop recording. Called via Ctrl+R."""
    _ensure_state()
    if state.rec_active:
        stop_and_save()
    else:
        start()

def start():
    _ensure_state()
    if state.rec_active:
        return
    state.rec_active = True
    state.rec_frames = []
    state.rec_frame_count = 0
    state.rec_started_at = time.time()
    _set_status("REC STARTED", 8)

def stop_and_save():
    _ensure_state()
    if not state.rec_active:
        return
    state.rec_active = False
    frames = state.rec_frames or []
    state.rec_frames = None
    state.rec_frame_count = 0
    if not frames:
        _set_status("REC STOPPED (NO FRAMES)", 8)
        return

    # Pick format: MP4 if imageio-ffmpeg is present, else GIF
    fmt = _choose_format()

    try:
        if fmt == "mp4":
            path = _save_mp4(frames)
        else:
            path = _save_gif(frames)
        kb = os.path.getsize(path) // 1024
        if kb >= 1024:
            size_str = f"{kb/1024:.1f}MB"
        else:
            size_str = f"{kb}KB"
        _set_status(f"REC SAVED: {size_str}", 11)
        print(f"Recording saved: {path}")
    except Exception as e:
        _set_status(f"REC FAILED: {e}", 8)
        # Print full exception so users can debug
        import traceback
        traceback.print_exc()

def _choose_format():
    """Returns 'mp4' if MP4 encoding is available, else 'gif'.

    Can be overridden via the config field 'recording_format'
    ('mp4', 'gif', or 'auto')."""
    try:
        from . import config
        cfg = config.get_config()
        forced = cfg.get("recording_format", "auto")
    except Exception:
        forced = "auto"

    if forced == "gif":
        return "gif"
    if forced == "mp4":
        return "mp4"

    # auto: prefer mp4 if available
    try:
        import imageio  # noqa: F401
        import imageio_ffmpeg  # noqa: F401
        return "mp4"
    except ImportError:
        return "gif"

def cancel():
    """Discard recording without saving. (Not currently bound to a hotkey.)"""
    _ensure_state()
    state.rec_active = False
    state.rec_frames = None
    state.rec_frame_count = 0
    _set_status("REC CANCELLED", 8)

# ----------------------------------------------------------------------
# FRAME CAPTURE (called from main loop)
# ----------------------------------------------------------------------

def maybe_capture_frame():
    """Called once per engine frame. Captures every Nth frame if recording."""
    _ensure_state()
    if not state.rec_active:
        return

    state.rec_frame_count += 1
    # Capture every FRAME_SKIP-th engine frame
    if state.rec_frame_count % FRAME_SKIP != 0:
        return

    # Auto-stop if hit duration limit
    if len(state.rec_frames) >= MAX_FRAMES:
        _set_status(f"REC AUTO-STOP ({MAX_DURATION_SEC}s)", 9)
        stop_and_save()
        return

    if state.screen is not None:
        # Snapshot current frame BEFORE the REC indicator gets drawn,
        # otherwise the indicator would be in the recording too.
        # Caller handles ordering: capture before indicator.
        state.rec_frames.append(state.screen.copy())

# ----------------------------------------------------------------------
# REC INDICATOR (drawn on top of the frame after capture)
# ----------------------------------------------------------------------

def draw_indicator():
    """Draws the small red REC dot in the top-right corner.
    Must be called AFTER maybe_capture_frame so the dot doesn't get
    baked into the recording."""
    _ensure_state()
    if not state.rec_active:
        # Show fading status message even when not recording
        _draw_status_message()
        return

    surf = state.screen
    if surf is None:
        return

    # Pulse the dot (visible 0.5s on, 0.3s off)
    elapsed = time.time() - state.rec_started_at
    pulse_phase = (elapsed * 1.5) % 1.0
    visible = pulse_phase < 0.7

    from .core import WIDTH
    from .graphics import rectfill, text

    # Background bar
    rectfill(WIDTH - 30, 1, 28, 7, 0)
    if visible:
        # Red dot
        rectfill(WIDTH - 28, 3, 3, 3, 8)
    text("REC", WIDTH - 22, 2, 8 if visible else 5)

    # Frame counter / time
    if state.rec_frames is not None:
        sec = int(elapsed)
        text(f"{sec:02d}S", WIDTH - 30, 10, 7)

    _draw_status_message()

def _draw_status_message():
    """Draw recent status messages (visible for ~3 seconds)."""
    if not state.rec_status:
        return
    age = state.frame_count - state.rec_status_time
    if age > 180:   # 3 sec at 60 fps
        return
    from .core import WIDTH
    from .graphics import rectfill, text
    msg = state.rec_status
    w = len(msg) * 4 + 6
    x = WIDTH - w - 2
    y = 22
    rectfill(x, y, w, 9, 0)
    text(msg, x + 3, y + 2, state.rec_status_color)

def _set_status(msg, color=7):
    state.rec_status = msg
    state.rec_status_color = color
    state.rec_status_time = state.frame_count

# ----------------------------------------------------------------------
# GIF EXPORT
# ----------------------------------------------------------------------

def _save_gif(frames):
    """Save frames as animated GIF. Returns the file path."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "GIF export needs Pillow: pip install pillow"
        )

    # Output directory
    out_dir = _output_dir()
    os.makedirs(out_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"rec_{timestamp}.gif")

    # Convert each pygame surface to PIL image
    pil_frames = []
    for surf in frames:
        # pygame.image.tobytes returns RGB bytes
        try:
            data = pygame.image.tobytes(surf, "RGB")
        except AttributeError:
            # Older pygame versions used tostring instead
            data = pygame.image.tostring(surf, "RGB")
        size = surf.get_size()
        img = Image.frombytes("RGB", size, data)
        # Quantize to 256-color palette (smaller file, matches engine vibe)
        img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
        pil_frames.append(img)

    # Frame duration in ms. We capture every FRAME_SKIP-th 60-fps frame,
    # so output runs at 60/FRAME_SKIP fps.
    duration_ms = int(1000 * FRAME_SKIP / 60)

    pil_frames[0].save(
        path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=duration_ms,
        loop=0,                     # loop forever
        optimize=True,
        disposal=2,                 # restore to background each frame
    )
    return path

# ----------------------------------------------------------------------
# MP4 EXPORT (preferred, smaller files, better quality, longer recordings)
# ----------------------------------------------------------------------

# 4x nearest-neighbor upscale for a sharper look on YouTube/Twitter,
# where 256x224 native would be re-compressed badly. 4x = 1024x896 keeps
# pixels crisp.
MP4_UPSCALE = 4

def _save_mp4(frames):
    """Save frames as an MP4 (H.264). Returns the file path."""
    try:
        import imageio
        import imageio_ffmpeg  # noqa: F401  (just to verify it's there)
    except ImportError:
        raise RuntimeError(
            "MP4 export needs imageio + imageio-ffmpeg: "
            "pip install imageio imageio-ffmpeg"
        )

    out_dir = _output_dir()
    os.makedirs(out_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"rec_{timestamp}.mp4")

    # FPS: capture every FRAME_SKIP-th 60-fps frame -> 30 fps output
    fps = 60 / FRAME_SKIP

    # Convert pygame surfaces to numpy frames, upscaled
    try:
        import numpy as np
    except ImportError:
        raise RuntimeError("MP4 export needs numpy")

    # imageio expects (height, width, 3) uint8 arrays, RGB
    writer = imageio.get_writer(
        path,
        fps=fps,
        codec="libx264",
        quality=8,                   # 0..10, higher = bigger but better
        macro_block_size=1,          # so 256x224 doesn't get padded
        pixelformat="yuv420p",       # widest compatibility (Twitter, etc.)
    )

    try:
        for surf in frames:
            # pygame surface -> numpy array (W, H, 3) -> (H, W, 3)
            arr = pygame.surfarray.array3d(surf).transpose(1, 0, 2)
            if MP4_UPSCALE != 1:
                arr = np.repeat(np.repeat(arr, MP4_UPSCALE, axis=0),
                                MP4_UPSCALE, axis=1)
            writer.append_data(arr)
    finally:
        writer.close()

    return path

def _output_dir():
    """Where recordings are written."""
    try:
        from . import config
        cfg = config.get_config()
        # Sibling of carts_dir, just like cart_covers does it
        base = os.path.dirname(cfg["carts_dir"]) or "~/.py16"
    except Exception:
        base = "~/.py16"
    return os.path.expanduser(os.path.join(base, "recordings"))
