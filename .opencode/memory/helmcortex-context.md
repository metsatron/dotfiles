# HelmCortex Context

Cross-project context adapted from Claude memory.

## DotCortex and HelmCortex Relationship

- DotCortex manages the literate dotfiles and machine overlays
- HelmCortex is the broader knowledge, tooling, and workflow environment
- Canonical task tracking for DotCortex work lives in HelmCortex TODO files

## DotCortex Machine Architecture

- `all/` - cross-platform shared layer
- `linux/` - Linux shared layer
- `debian/` - Debian-family layer
- `devuan/` - Devuan or sysv-init layer
- `x230/` - X230 machine layer
- `t480s/` - T480s machine layer

## Doctrine Notes

- Technical choices are often filtered through a larger sovereign-computing framework documented in HelmCortex
- Preferences like Devuan over Ubuntu, X11 over Wayland, and Guile over heavier middleware stacks are intentional, not arbitrary
- Treat these as decision context, not as a license to ignore current repo instructions or concrete user requests

## Terminal Roadmap

- WezTerm is the current daily driver terminal
- KiTTY remains a future terminal vision rather than the current implementation target
- When editing present-day terminal behavior, optimize for WezTerm stability first
