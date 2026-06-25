# .p16canvas — AI Generation Cheatsheet

A compact, authoritative reference for generating valid `.p16canvas` files for the
py-16 Animator (v0.8). Everything below was verified by round-tripping through the
tool's own `save_p16canvas()` / `load_p16canvas()` functions.

> **Purpose for an AI:** when asked to "make a .p16canvas", emit a plain-text file
> that matches the spec in §1 exactly. Do not invent fields, compression, or binary
> encoding — the format is deliberately simple line-based hex.

---

## 1. File format (authoritative)

A `.p16canvas` file is **UTF-8 / ASCII plain text** with Unix line endings (`\n`).

```
# P16CANVAS 256x224 v2      <- header line (line 1)
<512 hex chars>             <- row y=0  (256 pixels x 2 hex chars)
<512 hex chars>             <- row y=1
...                         <- 224 data rows total
<512 hex chars>             <- row y=223
```

Hard rules:

- **Line 1 is the header.** Use exactly `# P16CANVAS 256x224 v2` for new files.
- **Canvas is fixed at 256 x 224 pixels** (width x height). No other size is valid.
- **Exactly 224 data rows**, one per scanline, top to bottom (`y = 0` first).
- **Each data row is 512 hex characters** = 256 pixels, **2 uppercase hex digits per pixel**.
- Each pixel value is a **palette index 0–255**, written as `00`–`FF`.
- Pixels in a row run **left to right** (`x = 0` first).
- The pixel at `(x, y)` lives at character offset `2*x` within data row `y`.

The tool writes uppercase hex (`format(c, "02X")`); lowercase also decodes fine on
load, but emit uppercase to match the canonical output.

### Indexing formula

For a flat pixel array `pixels[]` of length `57344` (= 256 × 224), row-major:

```
index   = y * 256 + x
row y   = pixels[y*256 : (y+1)*256]
hex row = "".join("%02X" % (c & 0xFF) for c in row_y)
```

---

## 2. Color / palette conventions

- Palette indices are **0–255**. The py-16 palette is freely assignable, but the
  default low 16 entries follow the usual fantasy-console layout (0 = black/empty,
  7 = white, plus reds/greens/blues/etc. across 1–15). Indices 16–255 cover the
  extended palette.
- **Index 0 is treated as transparent / empty** inside the Animator. On the 256-canvas,
  index-0 pixels are simply not drawn (the background shows through). If you want a
  solid black background, you generally still use `00` — there is no separate "opaque
  black" in the empty slot. Use a different dark index if you need guaranteed fill.
- **Index 7 (white) is only special for `.p16img` files**, not for `.p16canvas`.
  In a canvas, `07` is just an ordinary white pixel.

A fully empty/blank canvas is therefore 224 rows of `"00" * 256`.

---

## 3. Minimal valid example (tiny, illustrative)

A real file has 224 rows of 512 chars, which is too large to show literally. The
structure looks like this (rows abbreviated with `…`):

```
# P16CANVAS 256x224 v2
0000000000…0000        (row 0:   all transparent)
0000080808…0000        (row 1:   some red (08) pixels)
…
000000000C…0000        (row 223: one blue (0C) pixel near the end)
```

Anything between rows that isn't 512 (or legacy 256) hex chars is skipped by the
loader, so keep every data row exactly 512 chars.

---

## 4. Reference generator (Python) — verified

This is the recommended way for an AI to produce a file. It mirrors the tool's own
writer and its output was confirmed to load back identically via the tool's
`load_p16canvas()`.

```python
CANVAS_W, CANVAS_H = 256, 224
CANVAS_PIXELS = CANVAS_W * CANVAS_H          # 57344

def save_p16canvas(path, pixels):
    """pixels: flat list of 57344 palette indices (0-255), row-major (y*256 + x)."""
    assert len(pixels) == CANVAS_PIXELS, "need exactly 57344 pixels"
    with open(path, "w", newline="\n") as f:
        f.write("# P16CANVAS 256x224 v2\n")
        for y in range(CANVAS_H):
            row = pixels[y*CANVAS_W:(y+1)*CANVAS_W]
            f.write("".join("%02X" % (c & 0xFF) for c in row) + "\n")

# --- helpers to build the pixel buffer ---
def blank(color=0):
    return [color] * CANVAS_PIXELS

def put(px, x, y, c):
    if 0 <= x < CANVAS_W and 0 <= y < CANVAS_H:
        px[y*CANVAS_W + x] = c

def hline(px, x0, x1, y, c):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        put(px, x, y, c)

def vline(px, x, y0, y1, c):
    for y in range(min(y0, y1), max(y0, y1) + 1):
        put(px, x, y, c)

def rect_fill(px, x, y, w, h, c):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            put(px, xx, yy, c)

# --- example: blue field with a yellow diagonal ---
px = blank(12)                               # 12 = blue background
for i in range(min(CANVAS_W, CANVAS_H)):
    put(px, i, i, 10)                        # 10 = yellow diagonal
save_p16canvas("canvas_001.p16canvas", px)
```

### From a PNG (optional)

If generating from an image, resize/crop to exactly 256×224, then map each RGB
pixel to the nearest palette index and feed the resulting flat list to
`save_p16canvas`. The file format itself never stores RGB — only palette indices.

---

## 5. Filename & placement conventions

- Extension must be **`.p16canvas`**.
- The tool auto-names saves `canvas_001.p16canvas`, `canvas_002.p16canvas`, …
  (smallest free 3-digit number, `001`–`999`). Follow this when you want the tool to
  pick the file up predictably.
- **Load picks the most recently modified `*.p16canvas`** in the working directory —
  there is no file browser. To make the tool load *your* file, ensure it is the newest
  `.p16canvas` present (or the only one).

---

## 6. Loader tolerances & gotchas (so you don't trip them)

The tool's loader is lenient in specific ways. Stay inside the canonical format and
none of this bites you, but it's useful to know:

- **Header / comment lines:** any line starting with `#` is ignored, as are blank
  lines. The header is not strictly required for loading, but always include
  `# P16CANVAS 256x224 v2` for correctness and forward compatibility.
- **Row length decides the version, per line:**
  - `512` chars → V2, decoded as 2 hex digits per pixel (full 0–255). **Use this.**
  - `256` chars → legacy V1, decoded as 1 hex digit per pixel (only indices 0–15).
  - Any other length → the row is **silently skipped** (a common cause of "my canvas
    looks shifted/empty"). Pad/verify every row to 512 chars.
- **Extra rows beyond 224 are ignored**; fewer than 224 rows leaves the rest of the
  canvas as transparent `0`.
- **Don't mix V1 and V2 rows** in one file — keep all rows 512 chars.
- Values are masked with `& 0xFF`, so keep indices in `0–255`; out-of-range numbers
  wrap rather than error.

### Self-check before emitting

1. First line is exactly `# P16CANVAS 256x224 v2`.
2. Exactly 224 data rows follow.
3. Every data row is exactly 512 chars, all in `[0-9A-Fa-f]`.
4. Total pixels described = 224 × 256 = 57344.

---

## 7. Related py-16 formats (don't confuse them)

| Extension | Size | Header (v2) | Hex/pixel | Notes |
|-----------|------|-------------|-----------|-------|
| `.p16canvas` | 256×224 | `# P16CANVAS 256x224 v2` | 2 | This document. Full-screen painting. |
| `.p16sheet`  | 16×16 frames | `# P16SHEET 16x16 v2` | 2 | Sprite frames (one per row block). |
| `.p16mov`    | sequence | `# P16MOV MULTIMEDIA v2` | 2 | Multimedia timeline referencing frames. |
| `.p16img`    | 32×32 | (sprite-tool format) | — | Here index **0 and 7** are transparent. |

All share the V2 idea (2 uppercase hex chars per pixel = full 256-color range) and
the "lines starting with `#` are comments" convention, but **only `.p16canvas` is
256×224 with 512-char rows.** Use the right header and dimensions for the format you
actually intend to produce.
