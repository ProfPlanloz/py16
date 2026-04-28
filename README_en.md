py-16
A 16-bit era style fantasy console written in Python using Pygame.Key Specificationspy-16Resolution256 x 224 @ 60 FPSPalette256 colors (fully customizable)Sprite Sheet256 x 256 (1024 sprites @ 8x8)Sprite Sizes8x8 to 64x64 (spr(id, x, y, w, h, flip_x, flip_y))Map128 x 128 tilesSound8 channels, 4 waveforms (Square, Triangle, Saw, Noise)EditorsSprite (F1), Map (F2), SFX (F3), Music (F4), Code (F6)Cart FormatJSON with base64-encoded sheet (~140 KB)Installationpip install pygame                      # Required
pip install numpy pillow reportlab pypdf pymupdf   # Optional, for all features
Or install using optional groups:pip install py-16[all]      # Everything
pip install py-16[fast]     # Just numpy (performance boost)
pip install py-16[pdf]      # PDF export
pip install py-16[covers]   # PDF cover previews
Security Notepy-16 executes code within the cart as standard Python code—there is no sandbox. Only open carts from sources you trust.A malicious cart has the same permissions as any Python script: it can read/delete files, access the internet, microphone, webcam, or address book. This applies to both .p16 and .pdf carts. Treat carts like scripts, not like static images or songs.If you download carts from the web, review the code in the editor first (F6 -> F8 to load without execution -> inspect code before pressing F9 to reload/run).Quick Startimport py16

def init():
    py16.sset(8, 0, 8)          # Draw a red pixel into the sprite sheet
    py16.fset(1, 0, True)       # Set Flag 0 for Sprite 1

def update():
    if py16.btn('right'):
        pass # update logic here

def draw():
    py16.cls(0)                 # Clear screen with color 0
    py16.spr(1, 100, 50)        # Draw sprite 1 at 100, 50
    py16.text("HELLO", 4, 4, 7) # Write text at 4, 4 with color 7

py16.run(update, draw, init)
Module Structurepy16/
├── __init__.py        Public API (re-exports everything)
├── state.py           Central mutable state
├── core.py            Constants, palette, run(), auto-boot countdown
├── graphics.py        cls, pset, rect, line, text, camera, clip, pal/palt
├── sprites.py         spr, sset, sget, load_spritesheet
├── maps.py            mset, mget, draw_map, fset, fget
├── input.py           btn, btnp, mouse_*
├── audio.py           tone() + waveform generators
├── sfx_data.py        Data models for SFX/Music
├── tracker.py         Background sequencer with effects
├── mathx.py           rnd, flr, mid, sin, cos, atan2, t, fps
├── cart.py            save_cart, load_cart (.p16 and .pdf)
├── cart_pdf.py        PDF export with manual generation
├── cart_runtime.py    run_cart, push_cart, pop_cart (stack)
├── config.py          Manages ~/.py16/config.json
├── bios.py            BIOS screen with cart list and power menu
├── editors.py         Sprite and Map editors (F1/F2)
├── editors_audio.py   SFX and Music editors (F3/F4)
└── code_editor.py     Code editor (F6) with live-reload (F9)
BIOS and Boot Cartpy-16 can start directly into a cart or the BIOS screen:# Start a specific cart directly
python3 demo.py

# Start with a Boot Cart (automatically loads ~/.py16/carts/boot.p16,
# 3-second countdown; press ESC or any key for BIOS)
python3 -c "import py16; py16.run()"
The BIOS screen displays all carts in the cart directory and offers:Launch cart (Enter)Code editor for new projects (F6)Power menu for Shutdown/Reboot/Quit (F12)F12 acts as the universal "emergency exit" back to the BIOS—regardless of whether a cart has crashed or an editor is open.Cart DirectoryDefault: ~/.py16/carts/. Override via environment variable PY16_CARTS_DIR.Configuration in ~/.py16/config.json:{
  "carts_dir":      "~/.py16/carts",
  "boot_cart":      "boot.p16",
  "power_off_cmd":  "sudo poweroff",
  "reboot_cmd":     "sudo reboot",
  "boot_countdown": 3
}
Runtime Cart Switchingpy16.run_cart("/path/game.p16")      # Reset, old cart is discarded
py16.push_cart("/path/menu.p16")     # Stack: remember previous cart
py16.pop_cart()                      # Return to previous cart
py16.go_to_bios()                    # Back to BIOS
Fullscreen & Scalingpy16.toggle_fullscreen() # Or press F11 at runtime
Persistent configuration:{
  "fullscreen":     true,
  "display_scale":  "auto",        // or fixed factor like 4
  "hide_cursor":    "auto"         // hidden in fullscreen
}
At display_scale: "auto", py-16 chooses the largest integer scaling factor that fits your screen for crisp pixels. Letterboxing is handled automatically.API OverviewGraphicsFunctionPurposecls(c=0)Fill screen with colorpset(x, y, c) / pget(x, y)Set/Get individual pixelrect(x, y, w, h, c) / rectfill(...)Draw rectangleline(x0, y0, x1, y1, c)Draw linecirc(x, y, r, c) / circfill(...)Draw circletext(s, x, y, c=7)Draw text using built-in 3x5 fontcamera(x, y)Set camera offsetpal(c0, c1)Remap color c0 to c1palt(c, transparent)Set transparency for a colorSprites & MapsFunctionPurposespr(id, x, y, w=1, h=1, fx, fy)Draw sprite (id, position, size, flip)mset(cx, cy, id) / mget(cx, cy)Set/Get map tiledraw_map(cx, cy, sx, sy, w, h)Draw region of the mapfset(id, flag, value) / fget(id, flag)Set/Get sprite flags (0..7)AudioFunctionPurposesfx(id, channel=-1)Play SFX patchmusic(track_id)Play music track (-1 to stop)tone(pitch, dur, wave, ch)Low-level tone generationWaveforms: WAVE_SQUARE, WAVE_TRIANGLE, WAVE_SAW, WAVE_NOISEEditors & ToolsKeyEffectF1Toggle Sprite EditorF2Toggle Map EditorF3Toggle SFX EditorF4Toggle Music EditorF6Toggle Code EditorF9Reload Code (Live-update update/draw without restart)F5Save CartF8Load CartPDF Cart ExportCarts can be exported as PDFs including a manual and the embedded data:py16.export_pdf("game.pdf", title="MY GAME", author="ME")
The PDF includes:Cover Page in a classic box-art style.Manual Page generated from # @manual ... # @end comments in your code.Asset Pages displaying the sprite sheet, map, and SFX list.Code Listing in a vintage 80s style with line numbers.Cart Attachment the .p16 file is embedded as a PDF attachment.LicenseGPLv3. See LICENSE file for details.
