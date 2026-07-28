---
name: dither-backdrop
description: Generate pixel-faithful ordered-dither backdrops (HP VUE pyramid, early-KDE dithered gradients, halftone fills) with the dither-backdrop tool, and reverse-engineer new reference styles by pixel forensics. Load before creating or recreating any retro Unix/KDE wallpaper, backdrop, or root-window pattern for Redstone 9X schemes.
---

# Dither Backdrop — procedural retro wallpapers

Classic Unix backdrops are algorithms, not rasters: two palette colors plus an ordered-dither (Bayer) threshold matrix. The `dither-backdrop` tool (`~/.local/bin/dither-backdrop`, tangled from `tools-dither-backdrop.org`, Python+PIL — ImageMagick is NOT installed on the T480s) regenerates them at any size and palette, so scheme wallpapers live as versioned source.

## Styles and usage

```bash
dither-backdrop vue-pyramid out.png                          # faithful HP-UX 10 VUE backdrop
dither-backdrop vue-pyramid out.png --light '#a385a3' --dark '#604360'   # any palette
dither-backdrop vue-pyramid out.png --size 1920x1080         # band insets scale with size
dither-backdrop vgradient out.png --levels 16                # early-KDE dithered vertical gradient
dither-backdrop solid out.png --density 0.5                  # classic halftone root fill
```

Key flags: `--steps` (pyramid density ladder), `--band-x/--band-y/--band-y-bottom` (band geometry), `--phase` (dither matrix offset), `--levels`, `--density`.

## The measured VUE ground truth (do not re-derive)

- Exactly two colors: light `#505E85`, dark `#272E41` — every "shade" is dither density.
- Bayer 8×8 matrix; density ladder 1.0, .875, .75, .5, .25, .125, 0.
- Band insets on 1024×768: 24px horizontal, 16px TOP, 24px BOTTOM — vertically asymmetric BY DESIGN (the dark plateau sits above the front panel). Symmetric variants: pass equal `--band-y`/`--band-y-bottom`.
- Reconstruction verified 99.84% pixel-exact against the original's observable backdrop; residue is panel-occluded seams.

## Adding a new reference style — probe first, never eyeball

1. Get the reference PNG. Probe with PIL: unique colors in clean patches (a true dithered backdrop region has exactly 2), then local density in 8×8 windows (`count(light)/64`) along scan lines to find band/gradient structure.
2. Print the actual dither grid of each density as ASCII (`#`/`.`) and compare against Bayer thresholding — match the matrix and phase, don't assume.
3. Map geometry by bounding-box per density level (the VUE asymmetry was found this way, invisible to the eye).
4. Implement as a new style function in `tools-dither-backdrop.org`, tangle, then verify with a masked pixel-diff against the reference (mask = pixels whose whole 5×5 neighborhood is the two backdrop colors — windows/panels in screenshots poison naive masks).
5. A detector that reports 0% or 100% is broken, not informative — validate it on known files first (`identify` does not exist here; use ffprobe/PIL, and never trust a pipeline whose exit status comes from `head`).

## Scheme-engine integration (pipeline)

Schemes can anchor their wallpaper procedurally: give the scheme file `BACKDROP_STYLE`, `BACKDROP_LIGHT`, `BACKDROP_DARK` (plus optional `BACKDROP_ARGS`) and generate at apply/build time instead of shipping rasters. Check `sanctuary-redstone-9x-schemes.org` for the current state of this wiring before assuming it exists — if the vars are not yet consumed there, generation is manual (run the tool, place the PNG where the scheme's wallpaper convention expects it).
