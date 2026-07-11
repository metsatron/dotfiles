---
name: dotcortex-update
description: Run the diff-then-apply loom sweep across DotCortex-managed package managers (nala, guix, flatpak, snap, pip, npm, cargo, appimage, brew, dnf, termux-pkg, am) to update installed software on one machine at a time.
---

# DotCortex Software Update Sweep

Use this when asked to update installed software across DotCortex-managed package managers — "update everything," "run the package manager updates," "sync installed packages with the manifests." This is about updating already-declared software, not adding new packages (see `dotcortex-package-manifests` for that).

## Principle: diff before apply

Most managers have a `:diff` verb — run it first and look at the output before running `:apply`. Only `guix`, `brew`, `pipx`, `termux-pkg` have no diff verb; their `:apply` is an idempotent declarative sync, safe to run directly. Don't skip straight to `:apply` on a manager that has `:diff` just to save a step — the diff is the point, it's what makes the sweep visible instead of a blind fire-and-forget.

## Sweep list

Not every manager applies to every machine — `brew` is macOS-only, `dnf` is T480 (OpenMandriva)-only, `termux-pkg` is s24/Termux-only, `am` is opt-in. Skip a manager if its manifest doesn't exist on this host's overlay (see `dotcortex-packages` for manifest paths) rather than erroring.

```bash
cd ~/DotCortex

loom nala:diff && loom nala:apply       # Debian/apt
loom guix:apply                         # core profile (fast, idempotent)
loom flatpak:diff && loom flatpak:apply
loom snap:diff && loom snap:apply
loom pip:diff && loom pip:apply
loom pipx:apply
loom npm:diff && loom npm:apply
loom bun:diff && loom bun:apply
loom bunx:diff && loom bunx:apply
loom cargo:diff && loom cargo:apply
loom appimage:update
loom app:apply
loom brew:apply                         # macOS only
loom dnf:diff && loom dnf:apply         # T480 only
loom termux-pkg:apply                   # s24/Termux only
loom am:diff && loom am:apply           # opt-in AppMan
```

`loom guix:pull` (channel updates) is deliberately NOT part of the default sweep — it's slow (minutes) and network-heavy. Only run it if the user asks for it explicitly.

## Rules

- One machine at a time, and only with the user's go-ahead for that machine — this is not a background fleet-wide cron job. A manager's apply can prompt interactively (nala held-package prompts, sudo) or hit a real conflict needing judgment; don't force through a prompt or retry blindly.
- Report what actually changed per manager (from the diff, or from apply's own summary) — "ran the sweep" without saying what moved defeats the purpose.
- Never invoke Haiku for this — package manager applies aren't zero-ambiguity mechanical work. Use the main session or a Sonnet-tier subagent.
- This sweep never touches `.org` source or manifests. Adding, removing, or version-pinning a package is a separate, deliberate manifest edit — not something this skill does on its own initiative.
