---
name: dotcortex-update
description: Run the diff-then-apply loom sweep across DotCortex-managed package managers (nala, guix, flatpak, snap, pip, npm, cargo, appimage, brew, dnf, termux-pkg, am) to update installed software on one machine at a time.
---

# DotCortex Software Update Sweep

Use this when asked to update installed software across DotCortex-managed package managers — "update everything," "run the package manager updates," "sync installed packages with the manifests." This is about updating already-declared software, not adding new packages (see `dotcortex-package-manifests` for that).

## Principle: diff before apply

Most managers have a `:diff` verb — run it first and look at the output before running `:apply`. Only `guix`, `brew`, `pipx`, `termux-pkg` have no diff verb; their `:apply` is an idempotent declarative sync, safe to run directly. Don't skip straight to `:apply` on a manager that has `:diff` just to save a step — the diff is the point, it's what makes the sweep visible instead of a blind fire-and-forget.

## Sweep list

Not every manager applies to every machine — `brew` is macOS-only, `termux-pkg` is s24/Termux-only, `am` is opt-in. Skip a manager if its manifest doesn't exist on this host's overlay (see `dotcortex-packages` for manifest paths) rather than erroring.

`dnf` is not on this fleet. This skill used to say "dnf is T480 (OpenMandriva)-only"; T480 was verified on 2026-07-13 to run **Vendefoul 6 with nala/apt and no dnf binary at all**, so T480 sweeps exactly like the other Debian-family machines. The `dnf` verbs are kept for a future RPM host, not for T480.

```bash
cd ~/DotCortex

loom nala:diff && loom nala:apply-auto  # Debian/apt — see TTY note below
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
herdr-stack-update --dry-run            # herdr + herdr-web pair (see gate note below)
loom brew:apply                         # macOS only
loom dnf:diff && loom dnf:apply         # RPM hosts only — NOT T480 (it is apt/nala)
loom termux-pkg:apply                   # s24/Termux only
loom am:diff && loom am:apply           # opt-in AppMan
```

`loom guix:pull` (channel updates) is deliberately NOT part of the default sweep — it's slow (minutes) and network-heavy. Only run it if the user asks for it explicitly.

## herdr moves only through its gate

`herdr` and `herdr-web` are version-pinned in the app manifest and NEVER updated by grabbing latest: the herdr-web bridge (third-party, kcosr/herdr-web) caps the herdr daemon protocol it can speak, and a herdr release that outruns the bridge silently kills phone/web access (the 0.7.5/protocol-17 incident, 2026-07-27). `herdr-stack-update --dry-run` runs the real handshake gate (sandboxed daemon + bridge on loopback — it never touches live services) and prints PROMOTE/HOLD verdicts per component. If it says PROMOTE, run `herdr-stack-update --apply` (add `--handoff` if a live server is running and herdr itself is promoting), then bump the two pins in `app.org` to the promoted versions in the same session so the manifest matches reality. Never run bare `herdr update` — it installs latest unconditionally, straight past the gate.

## nala needs a TTY — use `nala:apply-auto` from an agent session

`nala:apply` runs a bare `sudo nala upgrade`, and nala refuses to proceed without a terminal ("It can be dangerous to continue without a terminal"). An agent's Bash tool has no TTY, and neither does Claude Code's `!` prefix, so `nala:apply` simply cannot complete from a session — it dies after printing the upgrade plan. `nala:apply-auto` is the same recipe with `--assume-yes`; use it whenever running the sweep as an agent. `nala:apply` stays the human verb, for when Mètsàtron wants to eyeball the package list in a real terminal before confirming.

Both verbs run `upgrade`, never `full-upgrade` — held-back packages (kernel/ABI transitions) stay held either way and remain a deliberate human decision.

## Rules

- One machine at a time, and only with the user's go-ahead for that machine — this is not a background fleet-wide cron job. A manager's apply can hit a real conflict needing judgment; don't force through a prompt or retry blindly. `nala:apply-auto` is the one sanctioned non-interactive escape hatch, and only because nala's own prompt is a TTY check rather than a judgment call — never invent an `--assume-yes`/`--force` for any other manager to get past something it is asking about.
- Report what actually changed per manager (from the diff, or from apply's own summary) — "ran the sweep" without saying what moved defeats the purpose.
- Never invoke Haiku for this — package manager applies aren't zero-ambiguity mechanical work. Use the main session or a Sonnet-tier subagent.
- This sweep never touches `.org` source or manifests. Adding, removing, or version-pinning a package is a separate, deliberate manifest edit — not something this skill does on its own initiative.
