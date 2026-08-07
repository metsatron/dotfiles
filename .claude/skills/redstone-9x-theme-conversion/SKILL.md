---
name: redstone-9x-theme-conversion
description: The iron protocol for converting, rebuilding, or fixing ANY Redstone 9X theme family (Windows 95/98/2000 schemes, Plus!95/Kids, SerenityOS). Load BEFORE touching redstone-9x-theme-convert, classic-build, theme payload dirs, or theme org sources — carries the NEXUS source map, the sanctioned batch lanes, the trial gate, the artifact verification harnesses, and the traps that unwrote weeks of work on 2026-08-07.
---

# Redstone 9X Theme Conversion — The Iron Protocol

Load this BEFORE touching `redstone-9x-theme-convert`, `redstone-9x-classic-build`, any theme payload under `linux/.icewm/themes/` or `linux/.themes/`, or any `sanctuary-redstone-9x-*.org` theme source. It exists because 2026-08-07 proved what happens without it: an Opus session re-converted a fleet of themes ad hoc, silently dropped GTK4 everywhere, and unwrote weeks of work. Every rule below was paid for that night.

## Rule 1 — Never convert ad hoc. The lanes are the only door.

| Family | Command | Sources |
|--------|---------|---------|
| Windows 95 / 98 / 2000 default schemes | `redstone-9x-classic-schemes-import <win95\|win98\|w2k>` | NEXUS `themes/win95-schemes/`, `win98-schemes/`, `win2000-schemes/` (checksummed INFs from real install media) |
| Plus!95 / Plus! for Kids (16) | `redstone-9x-plus95-import` | NEXUS `themes/js98/` (FLAT_TITLE=1 + Chicago95 icons baked into the lane) |
| SerenityOS variants (32) | `redstone-9x-serenity-themes-import` | NEXUS `themes/serenity/` + `themes/serenity-retired/` (also regenerates the Start buttons — see the serenity-pipeline skill) |
| Legacy SerenityOS scheme | `redstone-9x-serenity-import <nexus-checkout>` | same checkout; its GTK theme is retired — the scheme rides `Serenity-Default` |

Era flags (FLAT_TITLE, icon themes) live INSIDE the lanes. Calling `redstone-9x-theme-convert` directly for a lane-owned family bypasses the era law and WILL ship wrong output.

## Rule 2 — Sources live in NEXUS. Only in NEXUS.

`~/HelmCortex/NEXUS/sanctuaries/sanctuary-redstone-9x/` (manifest: its `README.md`) is the sole sanctioned source archive — reachable fleet-wide via the `~/HelmCortex` symlink. Disc images (ISOs, media archives) stay in `t480s:~/Downloads/` by ruling; NEXUS holds curated assets only. A pipeline reading `~/Downloads`, `/tmp`, or a scratchpad as source is a defect: archive the source first, add its README row, then reference it.

## Rule 3 — Engine-first. Artifacts regenerate; they are never patched.

Fix the `.org` source, `tangle-one <file>.org`, rerun the lane. The emitted theme dirs for lane-owned families are REGENERATED OUTPUT — a hand-edit there is destroyed by the next lane run and silently diverges before that. (Non-lane vendored dirs — BeOS tabs, CDE massage themes — remain directly edited per the theme-pixels skill; know which kind you are touching before you type.)

## Rule 4 — The trial gate. One theme, landed, judged, THEN the batch.

Convert one representative theme, land it, and get Mètsàtron's live verdict before batch-running a family. The batch is cheap after the gate and ruinous before it. "We must fix it properly" — the ruling that governs this repo — means the engine is corrected once and the family rebuilt once, not that fifteen themes get patched fifteen ways.

## Rule 5 — Verify in artifacts before claiming anything.

- Pixel-probe emitted pixmaps (PIL): titlebar gradient endpoints from `titleAB.xpm`/`titleIB.xpm`, glyph bounding boxes, zero-pure-white checks on dark faces. A conversion that "exited 0" proves nothing about colours.
- Machine-validate every emitted GTK3 `gtk.css` — parse errors silently kill the entire provider and GTK falls back to Adwaita without a word:

```python
import gi; gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
errs = []; p = Gtk.CssProvider()
p.connect('parsing-error', lambda pr, s, e: errs.append(e.message))
p.load_from_path('<theme>/gtk-3.0/gtk.css'); print(len(errs), errs[:3])
```

- NEVER pipe a converter through `head` — `head` closes the pipe, the converter dies of SIGPIPE mid-emission, and you commit a half-built theme (this deleted a gtk-4.0 tree on 2026-08-07). Redirect to a log file and read the log.

## Rule 6 — Landing is Mètsàtron's hand, and gap-fill eats silent edits.

Remote git on the fleet is hook-guarded; hand Mètsàtron the land line to run via `!`. The line must remove the GUEST copies of every CHANGED theme dir before `loom redstone:refresh` — IceWM dirs, GTK dirs under the guest `.themes`, and icon-theme dirs alike — because the refresh gap-fills only MISSING dirs (full law + open re-projection mystery: the theme-pixels skill).

## Rule 7 — The colour law and the vocabulary.

- No made-up values: declared keys verbatim; absent keys fall back only to values proven from real install media or period footage (active caption default `#1084D0`; absent inactive gradient = SOLID); Windows 95 era = `FLAT_TITLE=1`.
- **Mètsàtron's "base" means the FACE** (`FOX_BASE`) — never GTK `base_color` data-white. Mistranslating this cost three live rounds.
- When the screen disagrees with the artifact, the screen wins: check WHICH theme is actually live (guest `.icewm/theme`) before diagnosing anything — hours went to judging a stale legacy theme while the fixed variants sat unviewed — then use the theme-pixels skill's live grid and marker experiment.

## Canonical Owners

- Engine + lanes: `sanctuary-redstone-9x-scheme-builders.org`; shared glyph/gradient: `sanctuary-redstone-9x-schemes.org`
- Source archive: `~/HelmCortex/NEXUS/sanctuaries/sanctuary-redstone-9x/` (its README is the manifest)
- Sibling skills: `redstone-9x-serenity-pipeline`, `redstone-9x-theme-pixels`, `redstone-9x-refresh`
- This skill: `agents-skills-dotcortex.org`
