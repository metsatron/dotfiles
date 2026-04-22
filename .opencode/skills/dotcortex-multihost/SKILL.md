---
name: dotcortex-multihost
description: Multi-machine DotCortex guidance for X230, T480s, overlay scoping, and HelmCortex integration.
---

# DotCortex Multi-Machine Setup

Use this skill when the task depends on which machine is being targeted, which overlays apply, or how HelmCortex is mounted.

## Machines

- `x230` - Debian and systemd, HelmCortex native, overlays `all linux debian x230`, apply with `loom stow:x230`
- `t480s` - Devuan and sysv-init, HelmCortex usually mounted then symlinked, overlays `all linux debian devuan t480s`, apply with `loom stow:t480s`
- future machines - clone DotCortex, run `INSTALL.sh`, then add only the overlays the machine truly owns

## Overlay Scoping

- `all/` - shared cross-platform layer
- `linux/` - Linux-only wrappers and config
- `debian/` - Debian-family package and distro layer
- `devuan/` - sysv-init shared layer
- `x230/` - X230-specific machine layer
- `t480s/` - T480s-specific machine layer

## HelmCortex Integration

DotCortex does not stow HelmCortex-owned configs. The boundary is deliberate.

DotCortex's normal touchpoint is PATH wiring for tools under `~/HelmCortex/FORGE/bin`.

`~/HelmCortex` may itself be a symlink to a mounted location such as `~/mnt/x230/HelmCortex`.

## SSH And PATH Note

Guix-managed tools may not be visible from plain bash or SSH PATH until `~/.guix-extra-profiles/core/core/bin/` is added.

## Bootstrap Rule

Fresh machines should start with:

```bash
cd ~/DotCortex && bash INSTALL.sh
```

Use this skill together with `dotcortex-bootstrap` or `dotcortex-gotchas` when the multihost layout is relevant to a failure.
