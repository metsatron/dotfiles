---
name: dotcortex-package-manifests
description: Manage DotCortex package manifests by editing root org sources, preserving manifest conventions, tangling safely, and applying changes through Loom or make-based fallbacks.
---

# DotCortex Package Manifest Operations for OpenCode

Use this skill when the task is specifically about package manifests in DotCortex rather than general dotfile editing.

## Use This Skill For

- adding or removing packages from a managed manifest
- updating package manifest entries in DotCortex
- comparing installed packages to manifest state
- applying manifest changes with Loom or make targets
- identifying which org file owns a package manifest
- working with pip, npm, guix, flatpak, snap, cargo, appimage, homebrew, or app manifests

## Do Not Use This Skill For

- general dotfile edits unrelated to package manifests
- direct overlay or stow troubleshooting
- Makefile or Loom control-plane work outside package operations

Use `dotcortex-loom` instead when the task is broader than manifest management.

## Critical Safety Rules

1. Never edit tangled output in overlay directories directly.
2. Edit the owning root `.org` file.
3. Never edit `Makefile` directly; edit `loom.org` if the task truly requires control-plane changes.
4. Preserve existing manifest structure and formatting conventions.
5. Prefer Loom verbs when available; otherwise use the matching `make` targets or existing helper scripts.
6. Check Guix profile bins before assuming package tools are unavailable.

## Repo Root

Assume the repo root is:

```bash
~/DotCortex
```

## Manager Map

| Manager | Org Source | Tangled Manifest | Preferred Verbs |
|---------|------------|------------------|-----------------|
| pip | `pip.org` | `all/.pip/manifest/packages.ssv` | `loom pip:apply`, `loom pip:diff`, `loom pip:capture`, `loom pip:health` |
| npm | `npm.org` | `all/.npm/manifest/global.ssv` | `loom npm:apply`, `loom npm:diff`, `loom npm:capture`, `loom npm:health` |
| guix | `guix.org` | `.config/guix/manifests/*.scm` | `loom guix:apply`, `loom guix:pull` |
| flatpak | `flatpak.org` | `linux/.flatpak/manifest/apps.ssv` | `loom flatpak:apply`, `loom flatpak:diff` |
| snap | `snap.org` | `all/.snap/manifest/apps.ssv` | `loom snap:apply`, `loom snap:diff` |
| cargo | `cargo.org` | `all/.cargo/manifest/crates.ssv` | `loom cargo:apply`, `loom cargo:diff` |
| appimage | `appimage.org` | `all/.appimage/inventory/all.ssv` | `loom appimage:update` |
| homebrew | `homebrew.org` | `all/.homebrew/manifest/brews.ssv` | `loom brew:apply` |
| app | `app.org` | `all/.app/manifest/apps.ssv` | `loom app:apply` |

## Ownership Lookup

If the manifest owner is unclear:

```bash
cd ~/DotCortex
grep -rn "tangle.*path/to/manifest/or/file" *.org
```

## Manifest Rules

### SSV-Based Manifests

Many DotCortex manifests use space-separated values with `""` for empty fields:

```text
# PKG VERSION EXTRA
litellm "" ""
openai "" ""
```

Rules:
- preserve existing comment headers
- preserve field order
- use `""` when the repo convention expects an empty value
- do not invent a new manifest layout for an existing manager

### Guix Manifests

Guix uses Scheme manifests instead of SSV.
Rules:
- follow the existing manifest style in `guix.org`
- do not convert Guix manifests into SSV
- validate via tangle and Guix/Loom workflows

## Standard Workflows

### Add a Package

1. Identify the correct manager and owning `.org` file.
2. Edit the manifest block in the root `.org` source.
3. Run:

```bash
cd ~/DotCortex
make tangle
```

4. Apply with the preferred Loom verb when available.
5. Report the source file changed, the generated manifest path, and the apply command used.

### Remove a Package

1. Remove the entry from the owning `.org` file.
2. Run `make tangle`.
3. Apply with the relevant Loom or make workflow.
4. Mention whether the manager removes extras automatically or only syncs additions.

### Diff Manifest vs Installed State

Use the manager-specific diff verb when available:

```bash
loom pip:diff
loom npm:diff
loom flatpak:diff
loom snap:diff
loom cargo:diff
```

If Loom is unavailable, use the repo's make targets or helper scripts where applicable.

### Capture Installed State

When the repo supports it, use capture verbs rather than manually reconstructing installed state:

```bash
loom pip:capture
loom npm:capture
```

Review capture results before assuming they should be committed as-is.

## Validation

After changing a manifest source, the default validation path is:

```bash
cd ~/DotCortex
make tangle
```

Then use manager-specific checks as appropriate:
- `loom pip:diff`
- `loom pip:health`
- `loom npm:diff`
- `loom npm:health`
- `loom flatpak:diff`
- `loom snap:diff`
- `loom cargo:diff`
- `loom guix:apply` or `loom guix:pull` for Guix workflows

## Fallback Behavior

If Loom is unavailable:
- use the matching `make` target when one exists
- otherwise use the existing repo helper scripts
- mention that Loom depends on Guix's `guile`

## Repo-Specific Gotchas

- root `.org` files are canonical; overlays are generated output
- first tangle on a fresh machine may require empty `.mk` stubs in `all/.mk/`
- first stow on a fresh machine should use `make safe-stow`, not Loom
- Guix tools may only be visible in `~/.guix-extra-profiles/core/core/bin/`
- `/tmp` permissions can break tangle and Guix operations
- old `.dotfiles` symlinks can cause stow ownership conflicts
- HelmCortex is separate and should not be treated as a DotCortex package manifest target

## Reporting Expectations

When completing a manifest task:
- name the `.org` source file changed
- name the manifest or output path affected
- mention whether `make tangle` was run
- mention whether apply, diff, or health commands were run
- call out any Guix, bootstrap, or machine-specific constraints
