---
title: "Redstone 9X"
description: "Mineshaft Whistler Redstone 9X First Edition™ Plus — the 1990s gaming habitat."
skin: redstone
weight: 2
---

Full name: **Mineshaft Whistler Redstone 9X First Edition™ Plus**. If you know, you know.

Redstone 9X is the gaming wing's first sanctuary: a container wearing the full desktop grammar of a late-1990s PC — teal desktop, battleship-grey chrome, and window furniture that behaves the way window furniture used to behave. Under the period costume it is a modern, declared system: IceWM shaped to the era, a DOSEMU2 terminal lane, a DOSBox-X compatibility lane, source ports for the classics, and a host-visible `.compat/` runtime spine that records how RetroPie collections, DOS projections, and per-lane state relate without flattening them into one folder. Every launcher is declared in DotCortex source rather than hand-installed — the whole thing rebuildable from the repo.

The point is not nostalgia for its own sake. The point is that the era's software is still excellent, still runs, and deserves a home that treats it as a living catalogue rather than a zip file in a downloads folder. Every launcher is declared in DotCortex source rather than hand-installed — the whole thing rebuildable from the repo.

The drywall is up:

![Redstone 9X — the Windows 95 theme in full regalia](/img/sanctuaries/redstone-9x/windows-95-theme.png)

Teal desktop, battleship-grey chrome, the taskbar and start menu behaving the way they used to. FVWM95 on the window-manager lane shaped to the era — not a screenshot of a 1995 machine, but a declared system rebuilding the grammar from source.

And underneath it, the conversion engine that makes the same room speak other lineages:

![Redstone 9X — SerenityOS theme conversion pipeline](/img/sanctuaries/redstone-9x/serenityos-pipeline.png)

`redstone-9x-theme-convert` + `redstone-9x-classic-build`: one shared engine that turns `.theme` and `.ini` files into IceWM themes, GTK themes, icon sets, fonts, and wallpapers — dispatching on whether the input parses as a Windows `[Control Panel\Colors]` block or a SerenityOS `[Colors]` block. Full toolkit compatibility: GTK 2/3/4, Qt 5/6, Fox, and Wine all inherit the same palette so a period-correct face renders across every application class, not just the window manager's own chrome. The SerenityOS variant count stopped at 32; the Windows 98 Plus! variants at 15. No theme left wearing another lineage's caption glyphs by accident.
