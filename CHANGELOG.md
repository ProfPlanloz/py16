# Changelog

All notable changes to py-16 are documented in this file.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026

second public release.

### Added

- 256x224 engine running at 60 FPS
- 256-color freely-assignable palette
- 256x256 sprite sheet (1024 sprites of 8x8) with multi-cel sprites and flipping
- 128x128 tile map with multi-layer rendering via sprite flags
- 8-channel audio system with 4 waveforms (Square, Triangle, Saw, Noise)
- Per-SFX-patch ADSR envelope (attack, decay, sustain, release)
- Pulse-width modulation for square waves (12.5%, 25%, 50%, 75%)
- SFX patches with tracker effects: slide, vibrato, drop, fade in/out,
  arpeggio fast/slow
- Music tracks built from pattern sequences, plays in background
- Built-in sprite editor (F1) with mouse pixel painter
- Map editor (F2) with scrollable map view and tile picker
- SFX editor (F3) with tracker grid, piano keyboard, and ADSR/PW panel
- Music editor (F4) for pattern and track composition
- Code editor (F6) with cursor, selection, clipboard, undo/redo, search,
  auto-indent
- Live reload (F9) for cart code without program restart
- `.p16` cart format (JSON with base64 sheet)
- `.pdf` cart format with cover, manual, asset overview and code listing -
  game cart and manual in one file
- Manual sections extracted from `# @manual ... # @end` comments
- BIOS screen with cart list, power menu, config management
- Auto-boot cart with countdown
- Cart stack (`run_cart`, `push_cart`, `pop_cart`) for runtime cart switching
- PDF cover previews in the boot-cart browser (with cache)
- Fullscreen mode (F11) with automatic scaling and letterboxing
- Linux power commands (poweroff/reboot) configurable
- Example boot cart with cover browser in 2x3 grid
- PDF metadata editor (F7) with live cover preview, color/font/image
  customization
- Demo cart with platformer, parallax, multi-layer map, sound demos

### Known limitations

- Cart code runs without sandbox - only load trusted carts
- Audio effects are simulated tick-by-tick, not streaming-smooth
  (16-bit character)
- Code editor displays lowercase letters as uppercase glyphs (original
  case is preserved in storage)
