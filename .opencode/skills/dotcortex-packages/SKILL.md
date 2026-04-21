---
name: dotcortex-packages
description: DotCortex package-manager architecture, manifest ownership patterns, and the add-a-new-manager workflow.
---

# DotCortex Packages

Use this skill when the task is about package-manager architecture, manager ownership, or adding a new manager to DotCortex.

For routine add or remove package edits inside an existing manager, use `dotcortex-package-manifests` instead.

## Manager Map

| Manager | Org File | Example Verbs |
|---------|----------|---------------|
| Guix | `guix.org` | `loom guix:apply`, `loom guix:pull` |
| Flatpak | `flatpak.org` | `loom flatpak:apply`, `loom flatpak:diff` |
| Nala and apt-backed repo state | `nala.org` | `loom nala:apply`, `loom nala:diff` |
| Snap | `snap.org` | `loom snap:apply`, `loom snap:diff` |
| Pip | `pip.org` | `loom pip:apply`, `loom pip:diff` |
| NPM | `npm.org` | `loom npm:apply`, `loom npm:diff` |
| Cargo | `cargo.org` | `loom cargo:apply`, `loom cargo:diff` |
| AppImage | `appimage.org` | `loom appimage:update` |
| Homebrew | `homebrew.org` | `loom brew:apply` |
| Apps | `app.org` | `loom app:apply` |
| Bun | `bun.org` | `loom bun:apply`, `loom bun:diff` |
| Bunx | `bun.org` | `loom bunx:apply`, `loom bunx:diff` |

`loom.org` is the live source of truth for verb coverage. Re-check it if the package surface appears to have moved.

## Manifest Convention

Many managers use space-separated values with `""` for empty fields:

```text
# PKG VERSION EXTRA
litellm "" ""
openai "" ""
```

Do not invent a new layout when an existing manager already has one.

## Add A New Package Manager

1. Create a new root-level `<manager>.org` file.
2. Add a manifest block with an explicit `:tangle` target.
3. Add capture, diff, apply, and health helpers under `all/.local/bin/` when the manager needs them.
4. Add a matching `.mk` fragment under `all/.mk/`.
5. Add the include to the Makefile block in `loom.org`, not to `Makefile` directly.
6. Add Loom verbs in `loom.org`.
7. Run `make tangle` and verify the new manager end to end.

## Rules

- root org sources are canonical
- manifests and helper scripts are generated output
- preserve existing field order and comment headers
- treat manager ownership as part of repo architecture, not just a list of packages
- Bun and Bunx now share `bun.org`; do not resurrect a standalone `bunx.org`
