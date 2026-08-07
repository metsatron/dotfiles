---
name: redstone-9x-serenity-pipeline
description: Where the SerenityOS upstream checkout lives and how Redstone 9X's two separate SerenityOS build pipelines work (the single legacy `serenity` scheme via redstone-9x-serenity-import, and the 32-variant `SerenityOS Themes` submenu + 15 Windows 98 Plus! themes via the shared redstone-9x-theme-convert/redstone-9x-classic-build engine). Load before touching anything SerenityOS-flavoured — icons, caption buttons, Start button, or adding/refreshing variants — so you don't rediscover the checkout location or reintroduce the Win95 donor's bar/square caption glyphs instead of SerenityOS's real triangles.
---

# Redstone 9X SerenityOS Pipeline — Where Things Live And How They're Built

Load this BEFORE touching anything SerenityOS-flavoured in Redstone 9X: the single legacy `SerenityOS` Desktop Scheme, the 32-entry `Themes > SerenityOS Themes` submenu, or the Serenity95 icon/GTK theme. There are TWO separate, differently-built pipelines that both produce "SerenityOS" output — conflating them, or fixing only one, silently leaves the other wrong (sealed 2026-07-25 after the first caption-button fix only covered the single legacy scheme and missed all 32 variants).

## The upstream checkout — find it before assuming you need to clone

A sparse SerenityOS checkout (`Base/res/` + `LICENSE` only, ~29 MB, upstream `https://github.com/SerenityOS/serenity`) was cloned into a session scratchpad on 2026-07-18 and has survived since: `/tmp/claude-1000/-home-metsatron-DotCortex/dcd9540e-ed5c-4d87-bbd1-4bf94055aa23/scratchpad/serenity`. Check this path FIRST — `/tmp` scratchpads are not durable (no guarantee across reboots or cleanup) so it may be gone by the time you read this; if so, re-clone from the same URL rather than guessing at a different source. It must contain `Base/res/icons/16x16/` (required by `redstone-9x-serenity-import`) and `Base/res/themes/*.ini` (required by `redstone-9x-theme-convert`, 23 files as of HEAD `75a8fe5`: `Basalt.ini`, `Coffee.ini`, `Redmond.ini`, etc. — names map directly to the Themes submenu entries). If you want it durable, mirror it into `~/HelmCortex/NEXUS/git/` alongside the existing `windows95` and `Obsidian-Win98-Edition` mirrors (see the `helmcortex-nexus` skill) — ask before doing this, it's the user's call.

If both the scratchpad and any NEXUS mirror are gone, the provenance is still recoverable: search the exported session corpus (see the `claude-session-logs` skill) for `SerenityOS/serenity` under the DotCortex project scope — the founding conversation (2026-07-19, session `05da60c9-cdd3-4387-8714-2c41df1`) has the user's original brief and the clone path.

## Two pipelines, not one

**`redstone-9x-serenity-import [serenity-checkout] [dotcortex-root]`** (`sanctuary-redstone-9x-scheme-builders.org`) builds ONLY the single legacy `SerenityOS` scheme (`ICEWM_THEME="Serenity"`, `MENU_BUTTON="serenity"`, top-level `Themes > SerenityOS` entry). It does a full crosswalk of upstream icon names to XDG names into `linux/.local/share/icons/Serenity95/`, clones `linux/.icewm/themes/Windows-95/` as its IceWM donor, and generates the matching GTK theme + `SerenitySans-Regular.ttf` + wallpaper. Idempotent, rerun with a checkout path to refresh from newer upstream — a full rerun `rm -rf`s and regenerates `linux/.icewm/themes/Serenity/` from scratch, so any hand-edit to that directory's output (not the generator) will be silently lost on the next run.

**`redstone-9x-theme-convert <file.theme> <ThemeName> <scheme-id>`** + **`redstone-9x-classic-build`** (same org file) build the 32 `Themes > SerenityOS Themes` submenu variants (`serenity-basalt`, `serenity-coffee`, `serenity-redmond`, …) AND the 15 `Windows 98 Plus!` variants — ONE shared engine for both families, dispatched by whether the input `.theme`/`.ini` file parses as a Windows `[Control Panel\Colors]` block or a SerenityOS `[Colors]` block (`redstone-9x-theme-convert` sets `icon='Win98SE'` vs `icon='Serenity95'` accordingly). `redstone-9x-classic-build` ALWAYS clones `~/HelmCortex/NEXUS/sanctuaries/sanctuary-redstone-9x/donors/Windows-95.tar.gz` as its donor (the canonical NEXUS source archive, reachable fleet-wide via the ~/HelmCortex symlink; byte-identical to the tracked `linux/.icewm/themes/Windows-95/`) regardless of which family is being built — so a SerenityOS variant and a Windows 98 Plus! variant start from the exact same donor pixmaps, diverging only by palette unless something explicitly branches on source type.

## The caption-button trap: SerenityOS uses triangles, the Win95 donor uses a bar/square

Real SerenityOS (`Userland/Services/WindowServer/WindowFrame.cpp`) falls back to `Base/res/icons/16x16/downward-triangle.png` (minimize) and `upward-triangle.png` (maximize) — small solid triangles, not the Win95 underline-bar / square-outline glyphs. Because BOTH pipelines clone the Win95 donor, EVERY SerenityOS-flavoured theme (the legacy scheme AND all 32 variants) ships the wrong glyph shape unless explicitly fixed. Real official assets used to verify this, fetched via `gh api repos/SerenityOS/serenity/git/trees/master?recursive=true` + `raw.githubusercontent.com`:
- Minimize/maximize: `Base/res/icons/16x16/downward-triangle-2x.png` / `upward-triangle-2x.png`
- Start-button mascot (legacy scheme's `MENU_BUTTON="serenity"`): `SerenityOS/artwork` repo, `images/ladyball.png` (the real "LadyBall" icon WindowFrame.cpp loads by name for its own start button) — NOT the wordmark-only `images/serenity_logo.png` (outline/stroke only, needs a real font-rendered word instead)
- Ladybird browser logo (for a Serenity-flavoured quick-launch Web Browser icon, if ever wired up): `LadybirdBrowser/ladybird` repo, `Base/res/icons/128x128/app-browser.png` (flat circular badge; the macOS `.iconset` variants have an unwanted black rounded-square background)

### Where the fix lives, per pipeline

- Legacy scheme: the triangle-drawing Python is baked directly into `redstone-9x-serenity-import`, right after the `redstone-9x-title-gradient` call, hardcoded to that scheme's own face colour `#d4d0c8`.
- The 32-variant + Plus! pipeline: the SAME triangle-drawing logic is baked into `redstone-9x-title-gradient` itself (the shared per-button glyph-recolour loop that already flips glyphs black→white for dark-faced themes), gated behind a `SERENITY_FACE` env var that `redstone-9x-theme-convert` only exports when `icon=='Serenity95'` — so Windows 98 Plus! conversions are never touched, and the shape swap automatically inherits the existing dark/light glyph-colour logic (draw the triangle in black, let the pre-existing `GL` recolour pass flip it if the face is dark).
- Both use identical geometry: 18×36 canvas, two 18×18 frames (`y0-17`=normal, `y18-35`=pressed), triangle centred at `(cx=8, top=6)` / `(cx=9, top=24)`, 7px wide tapering to a point over 4 rows.

### Retrofitting already-built output

The 32 variant directories under `linux/.icewm/themes/Serenity-*/` are vendored payload (git-tracked directly, not tangled) — a pipeline fix does NOT retroactively fix them. To patch already-built output without re-running the full converter (e.g. no checkout handy), read each variant's own `linux/.config/redstone-9x/schemes/serenity-<id>.scheme` for `FOX_BASE` (face colour) and `FOX_FG` (glyph colour when the face is dark, luminance < 96 — same threshold `redstone-9x-theme-convert` itself uses: `0.299*R + 0.587*G + 0.114*B`), then erase-and-redraw each `{minimize,maximize}{A,I}.png` directly. Verify with a byte-for-byte glyph-pixel-position diff against a known-good reference before trusting it, and always confirm on the live `:93` guest per `redstone-9x-theme-pixels` Law 0 — an already-deployed guest copy of a theme dir will NOT auto-refresh (Law 1 gap-fill trap applies here too, `rm -rf` the guest's copy of the specific theme dir before every refresh while iterating).

## Canonical Owners

- Generators: `sanctuary-redstone-9x-scheme-builders.org` (`redstone-9x-serenity-import`, `redstone-9x-theme-convert`, `redstone-9x-classic-build`)
- Shared glyph/gradient engine: `sanctuary-redstone-9x-schemes.org` (`redstone-9x-title-gradient`)
- Scheme declarations: `sanctuary-redstone-9x-schemes.org` (legacy `serenity`), generated `.scheme` files under `linux/.config/redstone-9x/schemes/serenity-*.scheme` (the 32 variants)
- Theme payload: `linux/.icewm/themes/Serenity/` + `linux/.icewm/themes/Serenity-*/` (vendored, edited directly)
- This skill: `agents-skills-dotcortex.org`
