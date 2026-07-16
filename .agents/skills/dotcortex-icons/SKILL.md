---
name: dotcortex-icons
description: Manage DotCortex icon themes, app icon aliases, pixel-art scaling, icon cache sync, and repo-backed icon payloads.
---

# DotCortex Icon Theme Workflows

Use this when adding, replacing, or debugging app icons in DotCortex-managed icon themes.

## Source Model

- Icon payloads live in `all/.local/share/icons` and `linux/.local/share/icons`.
- Live home roots such as `~/.local/share/icons` are cache/sync targets, not canonical source.
- `icons.org` owns helper scripts and process notes; edit it for workflow changes.
- Do not commit `icon-theme.cache` or `.icon-theme.cache`.

## THE THEMES ARE GIT SUBMODULES — a plain `git add` will not capture your icons

`Chicago95`, `BeOS-r5-Icons`, `Irixium`, `Iris`, `indigo-reality`, `Platinum9`, `irix-icons-linux` and `Throbbers` are each a **separate git repository** (mostly Mètsàtron's own GitLab forks). `icon-theme-inject` writes *inside* a submodule working tree. DotCortex only tracks the submodule's commit pointer, so from the DotCortex root your new PNGs appear as a single ` m <theme>` line and `git add <path/to/icon.png>` fails with *"Pathspec is in submodule"*. Commit them and they are silently absent.

Committing icon work is therefore always two steps:

```bash
SUB=~/DotCortex/linux/.local/share/icons/Chicago95
git -C "$SUB" add apps && git -C "$SUB" commit -m "feat(apps): ..."   # 1. inside the theme repo
git -C ~/DotCortex add linux/.local/share/icons/Chicago95             # 2. bump the pointer
```

Both need pushing for the icons to reach another machine — a DotCortex push alone carries a pointer to a commit that does not exist upstream.

**Keep injections additive.** `icon-theme-inject --names a,b,c` writes `a.png` and makes `b`/`c` symlinks to it — so an alias that collides with art the theme already ships will *overwrite upstream work* (it shows as `T` typechange, easily missed among a hundred `??` lines). Before committing, check `git -C "$SUB" status --short | grep -E '^ ?[MT]'` — that list should be empty. Restore anything on it.

## Workflow

1. Check current state:
   ```bash
   git status --short --branch
   gsettings get org.gnome.desktop.interface icon-theme 2>/dev/null || true
   xfconf-query -c xsettings -p /Net/IconThemeName 2>/dev/null || true
   kreadconfig6 --file kdeglobals --group Icons --key Theme 2>/dev/null || true
   ```
2. Find the app's desktop icon name:
   ```bash
   find ~/.local/share/applications /usr/share/applications \
     -maxdepth 1 -type f -iname '*APP*.desktop' \
     -exec sed -n '1,120p' {} \;
   ```
   Use the exact `Icon=` value first. Add app-id aliases for Flatpaks when useful.
3. Put source art through the helper, from the DotCortex root:
   ```bash
   all/.local/bin/icon-theme-inject ~/Pictures/icon.png \
     --themes Irixium,BeOS-r5-Icons \
     --names kitty \
     --resample nearest
   ```
   For fake-alpha art from image generators, add `--magic-pink` to turn exact
   `#ff00ff` pixels transparent before the per-size resize.
   If the matte is not exact or the icon has too much empty border, use
   `--transparent-tolerance N --trim-transparent`.
   Put the real icon id first in `--names`; extra aliases are symlinked unless
   `--copy-aliases` is passed.
4. Sync live icon roots:
   ```bash
   all/.local/bin/icons-home-sync --repo-root /home/metsatron/DotCortex
   ```
5. Verify files resolve through the live theme:
   ```bash
   find -L ~/.local/share/icons/Irixium ~/.local/share/icons/BeOS-r5-Icons \
     -type f -name 'kitty.png' -printf '%p %s bytes\n'
   ```

## Theme Layouts

- `Irixium`: `linux/.local/share/icons/Irixium/{16,22,24,32,48,64,128,256}x*/apps/NAME.png`
- `BeOS-r5-Icons`: `linux/.local/share/icons/BeOS-r5-Icons/apps/{16,22,24,32,48,64,128,256}/NAME.png`
- `indigo-reality`: `linux/.local/share/icons/indigo-reality/apps/{16,22,32,48,64,128}/NAME.png` plus `apps/256FIXED/NAME.png`

If a new theme has a different app-directory grammar, add it to `THEME_SIZES` and `theme_app_dir()` in `icons.org`.

## Pixel Art Rules

- **Non-square sources must use `--square`.** The default resize is `image.resize((size, size))`, which *stretches*. Game sprites are rarely square (Doom's `STFST01` is 24x29) and come out visibly squashed with no warning.
- **Choose by legibility at the smallest size actually used, not by what looks good at 128.** IceWM's `MenuIconSize=16`, so a Start-menu icon lives or dies at 16px. Render every candidate at 16/22/24/32/48, look at them side by side, and pick from that. Quake's Ranger HUD face is the perfect counterpart to the Doomguy's — and it is dark, low-contrast art that collapses into brown mush below 32px, so the Q logo won the slot. Photographic console art (the SNES/N64 renders in the BeOS pack) is gorgeous at 128 and an unreadable grey smear at 32.
- **Game art is already in the tree — extract, don't draw.** `game-art-extract` (sanctuary-retropie.org) pulls lumps from Doom IWADs and Quake PAKs at native size, in the original palette. Reach for it before inventing or downloading art.
- Pixel art: use `--resample nearest`; inspect 16/22/24 px outputs because readability can fail at panel size.
- ChatGPT-style magic-pink mattes: use `--magic-pink` or `--transparent-color '#ff00ff'`.
- Use `--transparent-tolerance` when the matte is slightly off-pink, and
  `--trim-transparent` to crop empty alpha borders while preserving square output.
- Smooth artwork: use `--resample lanczos`.
- Plasma/SonicDE panel icons need high-resolution sources; generate at least up
  to 128px or 256px to avoid ugly bilinear upscale from 48px.
- Generate real size-specific PNGs; never put a huge source PNG directly into tiny icon directories.
- Prefer exact square sources. If the source is not square, decide whether to crop, pad, or preserve aspect before generating.

## Cache Gotchas

- `icons-home-sync` removes repo-side icon caches and rebuilds live caches when possible.
- Some remixed themes can make `gtk-update-icon-cache` report an invalid cache while icon lookup still works. Verify actual files before assuming failure.
- If a panel or launcher keeps an old icon, restart the launcher/panel or log out/in after the files are correct.

## Useful Tools To Prefer

- Pillow: deterministic scripted resize; already works well for DotCortex helpers.
- ImageMagick: format conversion, inspection, sprite sheets, batch transforms.
- oxipng: lossless PNG optimization after generation.
- pngquant: lossy palette compression when small files matter.
- Aseprite or LibreSprite: manual pixel-art editing and per-size cleanup.
