---
name: dotcortex-multihost
description: Multi-machine deployment (X230, T480s), overlay scoping, HelmCortex integration, bootstrap fresh machines
---

# DotCortex Multi-Machine Setup (Star Fleet)

## Machines

- **X230** (ThinkPad, Debian/systemd): HelmCortex native, overlays: `all linux debian x230`, loom verb: `loom stow:x230`
- **T480s** (ThinkPad, Devuan/sysv-init): HelmCortex mounted at `~/mnt/x230/`, symlinked to `~/HelmCortex`, overlays: `all linux debian devuan t480s`, loom verb: `loom stow:t480s`
- Future machines: clone DotCortex, run `INSTALL.sh`, done

## Overlay Scoping

- `all/` — cross-platform (works on Linux, macOS, etc)
- `linux/` — Linux-only (Guix is Linux-only, so `host-wrap` lives here)
- `debian/` — Debian-family shared (apt/nala packages)
- `devuan/` — sysv-init shared (non-systemd daemons, desktop launchers for XFCE panel scripts)
- `x230/` — X230-specific (earlyoom, neofetch/fastfetch configs, GTK settings, wezterm, systemd services)
- `t480s/` — T480s-specific (future machine-specific configs)

## .zshenv for SSH PATH

The `.zshenv` file (tangled from `shell.org`) sources Guix profiles for ALL zsh invocations (login, interactive, scripts, SSH). This ensures `emacs`, `nvim`, `guile`, and other Guix tools are available over SSH without manual PATH setup.

## HelmCortex Integration

DotCortex (foundation) and HelmCortex (temple) are fully decoupled. DotCortex does **not** stow any files into HelmCortex — HelmCortex owns all its own configs (`.obsidian/`, `.vscode/`, FORGE/bin scripts, conda configs) directly.

DotCortex's only HelmCortex touchpoint is the shell PATH entry in `shell.org` / `.zshenv` that adds `$HOME/HelmCortex/FORGE/bin` to `$PATH` for tools like `auryn`, `helmcortex-anaconda`, and `claude-code-md-pipeline`.

HelmCortex lives at `~/HelmCortex` (may be a symlink to a mount point like `~/mnt/x230/HelmCortex`).

**Historical note**: HelmCortex configs were previously managed via `helmcortex.org` and stowed from `all/HelmCortex/`. This was decoupled in March 2026. The `style.org` laincore.css tangles directly to `~/HelmCortex/.obsidian/snippets/` (not through stow).

## Bootstrap (Fresh Machine)

```bash
git clone --recursive https://gitlab.com/metsarono/dotfiles.git ~/DotCortex
cd ~/DotCortex && bash INSTALL.sh
```

See `INSTALL.sh` for detailed phase-by-phase documentation including lessons learned on Guix installation, init system differences, and first-tangle bootstrapping.
