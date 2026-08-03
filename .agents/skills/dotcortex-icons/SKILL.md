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

## SE98 vs Win98SE — settled provenance, do NOT re-investigate (sealed 2026-07-31)

`SE98` and `Win98SE` are two applied instances of ONE upstream theme — `nestoris/Win98SE` on GitHub ("SE98 icon theme … based on Windows 98 SE style and grassmunk/Chicago95"; the author's own description: *"Enhanced Classic icon theme (used with Win98 Second Edition, WinME, Win2K systems)"*). That upstream ships both win2k and win98 variants of the version-specific icons, toggled by `win2k_icons.awk` / `win98_icons.awk`. DotCortex vendors two applied instances: **`Win98SE` = the win98 variant** (used by the `windows-98` scheme) and **`SE98` = the win2k variant** (used by the `windows-2000` scheme — it is genuinely Windows 2000/ME icons; 2000 and ME shared the set). The name "SE98" is the legitimate upstream project name, not a claim about the applied variant.

Decisive proof if you ever doubt it again: `SE98/devices/{16,32,48}/computer.png` is byte-identical to `computer_win2k.png`, while `Win98SE`'s is byte-identical to `computer_win98.png`. The ~90% byte-overlap between the two themes (7283/8119 files identical) is **expected** — one upstream, and 98/ME/2000 shared most of shell32 — it is **not** duplication to "clean up". `SE98` is intentional and correct for `windows-2000`, with no downstream modifications. Do NOT rename it, dedupe it against `Win98SE`, replace it, or "source real 2000 icons" — the icons are already correct; the only gap was this note.

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

## Inheritance: a child theme's GENERIC name beats the parent's SPECIFIC one

GTK's `choose_icon()` iterates **theme-first, not name-first**. Given `choose_icon(["folder-documents", "folder"])`, it tries *every* requested name in the child theme before falling through to the parent. So a child that defines only generic `folder` wins with `folder` — the parent's correct `folder-documents` is never reached.

Any theme with `Inherits=` that ships a partial `places/` set is exposed. Win31 and Serenity95 both inherited Chicago95 and defined only `folder`, so every user-space folder — including My Documents — rendered plain while the parent had correct art the whole time. Fix by giving the child its own copy of each specific name; do not "fix" the parent.

**Verify through the real call path.** `lookup_icon("folder-documents")` resolves correctly even when the desktop is visibly wrong, because a single-name lookup cannot express the fallback list. Reproduce with `choose_icon([...])` in the same order the consumer uses, or you will confirm a bug does not exist while looking straight at it.

## Cache Gotchas

- `icons-home-sync` removes repo-side icon caches and rebuilds live caches when possible.
- Some remixed themes can make `gtk-update-icon-cache` report an invalid cache while icon lookup still works. Verify actual files before assuming failure.
- If a panel or launcher keeps an old icon, restart the launcher/panel or log out/in after the files are correct.
- **`find` without `-L` reports a symlinked theme dir as empty.** `find <symlink-to-dir> -type f` returns nothing and `du -sh` shows 4.0K, which reads exactly like an empty directory. Six themes were reported as "empty dirs, nothing to migrate" on that basis when they were symlinks into a staging tree with 178 files behind them. Always `find -L` before concluding a theme has no content, and `ls -ld` before calling anything a directory.

## Useful Tools To Prefer

- Pillow: deterministic scripted resize; already works well for DotCortex helpers. **It cannot read every XPM** — its plugin handles only simple 1-char/pixel files, so the ice2k `Win2kmod-*` icons make it report *every* file in the tree as corrupt, touched or not. A checker that fails files you never modified is the checker failing; confirm with ImageMagick before believing damage.
- ImageMagick: format conversion, inspection, sprite sheets, batch transforms. The reliable XPM validator here — `convert f.xpm -format '%wx%h' info:`.
- oxipng: lossless PNG optimization after generation.
- pngquant: lossy palette compression when small files matter.
- Aseprite or LibreSprite: manual pixel-art editing and per-size cleanup.
