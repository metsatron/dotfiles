---
name: dotcortex-bootstrap
description: Fresh machine and recovery bootstrap skill.
---

# DotCortex Bootstrap

Use this for fresh-machine setup or recovery.

## Quick Path

```bash
git clone --recursive https://gitlab.com/metsarono/dotfiles.git ~/DotCortex
cd ~/DotCortex && bash INSTALL.sh
```

`INSTALL.sh` handles everything: system deps, Guix install, first tangle, first stow, pip/npm/cargo manifests.

## Manual Steps (when INSTALL.sh is unavailable)

1. Install system deps: `sudo apt install -y git stow emacs-nox python3 make`
2. Clone the repo to `~/DotCortex`
3. Create first-tangle stubs (the Makefile needs `.mk` fragments that don't exist yet):
   ```bash
   mkdir -p all/.mk
   for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
     [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
   done
   ```
4. Run `make tangle`
5. Run `STOW_PKGS='all linux debian devuan t480s' make safe-stow` (adjust overlay set for the target machine)
6. After first stow: `loom guix:apply && loom pip:apply && loom npm:apply`

## Rules

- Use `make safe-stow` for the first stow — loom is not yet functional (needs stowed `maak.scm` + Guix guile)
- After first stow, use `loom stow:x230` or `loom stow:t480s` for all subsequent stow operations
- For Guix on Devuan/sysv-init: install `daemonize` first, use the manual method from `INSTALL.sh`
- Use `ftp.gnu.org` directly for Guix downloads — the `ftpmirror.gnu.org` redirector sometimes has broken SSL

## Related Skills

- `dotcortex-multihost` — overlay scoping and machine-specific stow verbs
- `dotcortex-gotchas` — known failure modes during bootstrap
