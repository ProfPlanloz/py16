# py16os App Store — modular source

The app store is split into modules here (easier to maintain and version) and
bundled by `build.py` into **one** file, `dist/appstore.py` — because py16os
loads exactly one flat `.py` per plugin.

## Folder structure

```
appstore/
  src/
    appstore/
      __init__.py     Plugin interface: re-exports APP/init/update/draw
      config.py       Constants: REPO_BASE, ROUTING_RULES, APP, FILTERS, ROW_H
      state.py        Shared runtime state S (+ set_status)
      helpers.py      Pure helpers: routing, catalog, text, .p16img, layout
      tasks.py        Networking + background threads (refresh/install/icon)
      views.py        Drawing — draw()
      controller.py   Input — update() + init()
    build.py          Bundles src/appstore/*.py -> dist/appstore.py
  dist/
    appstore.py       AUTO-GENERATED — the deployable single file
  index.json          Sample catalog (with author/created/license/lang/tags)
```

## Build

```
cd appstore/src
python3 build.py        # produces ../src/dist/appstore.py
```

The bundler strips the package-internal (relative) imports, collects the
external imports once at the top, and merges the modules into a single
namespace in dependency order. `urllib` is kept lazy on purpose (imported
inside the function).

## Deploy

Copy `dist/appstore.py` to `apps/appstore.py` next to `py16os_cart.py`, then
type `RELOAD` in the py16os console. Alternatively, install it through the
store itself (the installer flattens `apps/appstore/appstore.py` to
`apps/appstore.py`).

## Why not run it as a package directly?

The host scans `apps/` for individual `.py` files and loads them flat; a
directory package with `__init__.py` + submodules would not be resolved as a
plugin. Hence: develop modular, ship bundled.

## Architecture in one sentence

`config` (fixed) -> `state` (S) -> `helpers` (pure) -> `tasks` (threads, write S)
-> `views`/`controller` (read S, draw or react to input). They all share the
single object `S` instead of scattered module globals.

## Download targets (routing)

On install, `ROUTING_RULES` in `config.py` decides where each file is written
locally:

| File type                        | Target       |
|----------------------------------|--------------|
| Plugin code `.py`                | `apps/`      |
| Plugin icon `.p16img` (apps/...) | `apps/`      |
| Standalone icon (py16img/...)    | `downloads/` |
| Cart `.pdf` / `.p16`             | `downloads/` |
| Wallpaper `.p16canvas`           | `downloads/` |
| Animation `.p16mov`              | `downloads/` |
| Spritesheet `.p16sheet`          | `downloads/` |
| everything else (fallback)       | `downloads/` |

In short: **apps stay in `apps/`, everything else goes to `downloads/`.**
`dest_for()` is the single source of truth — the installed status and the
icon loading in the info card automatically follow the same mapping.

Note: carts therefore no longer live in the root directory. If the host's
FILES app only scans the root directory for launchable carts, they may need
to be opened from `downloads/`, or the rule for `.pdf`/`.p16` set back to
`"."`.

## Real download counts (GitHub Releases)

The info card shows real download counts when the files exist as **release
assets** in the repo. GitHub counts asset downloads automatically
(`download_count`); the store reads them via the API:

```
GET https://api.github.com/repos/<owner>/<repo>/releases
```

`config.py` derives the URL from `REPO_BASE` (`RELEASES_API`). It is fetched
once on refresh and on the first opening of the info card (cached).

For the counts to be *real* and to actually *increase*, two things must hold:

1. The files exist as assets in a GitHub release (asset name = file name,
   e.g. `crypto_app.py`, `boot_cart.pdf`).
2. The install downloads from the asset URL — the store does this
   automatically: if an asset is known, `browser_download_url` is used (GitHub
   counts the download), otherwise it falls back to the raw path.

As long as an entry has no matching asset, the info card shows the static
`downloads` field from `index.json`. The live value thus beats the static
one, but only when an asset exists.

Limits: the GitHub API allows ~60 unauthenticated requests per hour per IP —
not a concern given the single, cached fetch. The number is "asset
downloads", not exactly "installs".

## Type icons (fallback instead of placeholder)

Entries without their own `.p16img` (carts, wallpapers, animations,
spritesheets) used to show a placeholder ("?") in the info card. Instead, a
**type icon** is now shown, depending on `item_kind`:

| kind     | File                 |
|----------|----------------------|
| `cart`   | `pdf.p16img`         |
| `canvas` | `p16canvas.p16img`   |
| `movie`  | `p16mov.p16img`      |
| `sheet`  | `p16sheet.p16img`    |

These files must exist locally. They are searched for in (first match wins):
`appstore/`, `apps/appstore/`, `apps/`, `.` — see `TYPE_ICON_DIRS` in
`config.py`. If a file is missing, the placeholder remains for that type.

The type icon also kicks in when an entry would have its own icon but it
cannot be loaded (e.g. a failed repo fetch).
