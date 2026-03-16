# DotCortex Reference

## What This Repo Is

DotCortex is a literate dotfiles system:

`root .org files -> make tangle -> overlay dirs -> make safe-stow -> $HOME`

Root `.org` files are canonical. Overlay directories are generated output.

## Critical Rules

1. Never edit tangled output under overlay directories.
2. Never edit `Makefile` directly; it is tangled from `loom.org`.
3. Use `make safe-stow` rather than raw `stow`.
4. Repo location is expected to be `~/DotCortex`.
5. New package manager support follows the existing pattern: `.org` source, SSV manifest, helper scripts, `.mk` fragment, Loom verbs.

## Overlay Scope

- `all/` - shared
- `linux/` - Linux-only
- `debian/` - Debian-family shared
- `devuan/` - sysv-init shared
- `x230/` - X230-specific
- `t480s/` - T480s-specific
- `arch/`, `osx/`, `be/`, `navi/` - other platform or machine overlays

## Standard Commands

```bash
cd ~/DotCortex
make tangle
make preview-stow
make safe-stow

# With Loom
loom
loom stow:x230
loom stow:t480s
loom stow:devuan
loom pip:apply
loom npm:apply
loom guix:apply
loom flatpak:apply
```

Without Loom, use the `make` targets directly.

## Ownership Lookup

To find which org file owns a generated config:

```bash
grep -rn "tangle.*path/to/config" *.org
```

Common owners:

- shell configs -> `shell.org`
- Makefile / Loom control plane -> `loom.org`
- Guix manifests -> `guix.org`
- theme and GTK settings -> `style.org`

## Package Manifest Notes

Manifest format is SSV with `""` for empty values:

```text
# PKG VERSION EXTRA
litellm "" ""
openai "" ""
```

Current manager sources:

- `pip.org`
- `npm.org`
- `guix.org`
- `flatpak.org`
- `snap.org`
- `cargo.org`
- `appimage.org`
- `homebrew.org`
- `app.org`

## Bootstrap Notes

- Fresh machine entry point: `bash INSTALL.sh`
- First tangle may need empty `.mk` stubs in `all/.mk/`
- Loom cannot be used for the very first stow on a fresh machine
- Guix tools may live in `~/.guix-extra-profiles/core/core/bin/`

## Known Gotchas

- `/tmp` permissions must be `1777` for tangle and Guix operations
- `grep -v` can fail under `set -euo pipefail` when it filters all lines
- absolute symlinks inside overlay output can break stow
- old `.dotfiles` symlinks can trigger `not owned by stow`
- `LD_PRELOAD` warnings around `libgtk3-nocsd` are usually cosmetic

## HelmCortex Boundary

DotCortex and HelmCortex are decoupled. DotCortex should not stow files into HelmCortex. The main integration point is PATH wiring for `~/HelmCortex/FORGE/bin`.
