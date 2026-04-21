---
name: dotcortex-gotchas
description: Troubleshooting DotCortex issues - stow conflicts, first-tangle failures, Guix bootstrap problems, and other known repo gotchas.
---

# DotCortex Gotchas

Use this skill when a DotCortex task is failing in a way that smells like bootstrap, tangle, stow, PATH, or machine-environment trouble.

## Canonical Rules First

- `Makefile` is tangled output from `loom.org`; never patch it directly
- root `.org` files are canonical; overlays are generated
- first stow on a fresh machine should use `make safe-stow`, not Loom

## Common Failures

### First tangle fails because `.mk` fragments do not exist

Create stubs first:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

### Loom bootstrap chicken-and-egg

`loom` needs both Guix's `guile` and the stowed `~/.config/maak/maak.scm`. On a fresh machine, use `make safe-stow` first. Do not assume `loom stow:x230` or `loom stow:t480s` works before that.

### Guix tools missing in SSH or bash sessions

Check `~/.guix-extra-profiles/core/core/bin/` before assuming the tool is absent.

Temporary bash fix:

```bash
export PATH="$HOME/.guix-extra-profiles/core/core/bin:$PATH"
```

### Old `.dotfiles` symlinks after repo rename

Stow may report `not owned by stow` if older symlinks still point at the previous repo path.

Cleanup:

```bash
find ~ -maxdepth 5 -lname "*/.dotfiles/*" -not -path "*/.git/*" -delete
```

### Stow conflict format differences

`safe-stow` has to handle at least these conflict shapes:

1. `existing target is neither a link nor a directory`
2. `cannot stow ... over existing target ...`
3. `existing target is not owned by stow`

If you are debugging stow behavior, remember that the repo already accounts for all three.

### Guix installer issues on Devuan or non-interactive shells

- install `daemonize` first on sysv-init systems
- prefer the manual install path documented in `INSTALL.sh`
- use `ftp.gnu.org` if `ftpmirror.gnu.org` has broken SSL

### `LD_PRELOAD` warning with `libgtk3-nocsd`

This is usually cosmetic. Ignore it or unset `LD_PRELOAD` if it becomes distracting.

### Absolute symlinks in overlay output abort stow

Machine-specific absolute links should not live in stow-managed overlays. Remove the generated absolute link and fix the owning source or bootstrap flow instead.

### `/tmp` permissions break both tangle and Guix

Symptoms include org persist temp failures and Guix sandbox bind errors.

Fix:

```bash
sudo chmod 1777 /tmp
```

Tangle-only workaround:

```bash
TMPDIR=~/.cache/tmp make tangle
```

### `pipefail` plus `grep -v`

Under `set -euo pipefail`, `grep -v` returns exit code `1` when it filters out every line. Wrap it as `{ grep -v PATTERN || true; }` when an empty pass-through is acceptable.

### Guix substituter progress crash

If `guix package` fails with a progress-display type error, retry. It is usually cosmetic and much of the work may already be cached.

## Reporting Rule

When using this skill, report the concrete symptom, the known gotcha that matches it, and the exact recovery command or source file to inspect.
