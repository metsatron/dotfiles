---
name: dotcortex-gotchas
description: Troubleshooting DotCortex issues — stow conflicts, tangle failures, Guix installer problems, LUKS gotchas, /tmp permissions
---

# DotCortex Known Gotchas

## Makefile is tangled output — never edit it directly

The Makefile is tangled from `loom.org`. Any direct edits will be overwritten by the next `make tangle`. Always edit the Makefile template block in `loom.org` instead, then re-tangle.

## First tangle fails with "No rule to make target .mk"

The Makefile includes `.mk` fragment files that don't exist until after the first tangle. `INSTALL.sh` handles this by creating empty stubs. If running manually:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

## Loom bootstrap (chicken-and-egg)

`loom` needs `~/.config/maak/maak.scm` (placed by stow) and Guix guile. You CANNOT use `loom stow:x230` for the first stow — use `make safe-stow` directly. `INSTALL.sh` handles this by pre-placing `maak.scm` before stow runs (Phase 5.5).

After the first `make safe-stow`, loom is functional and can be used for all subsequent stow operations.

## Guix emacs not in SSH PATH

On Guix machines, emacs lives at `~/.guix-extra-profiles/core/core/bin/emacs`. It is NOT in the default SSH PATH. The `.zshenv` file (tangled from `shell.org`) sources Guix profiles for ALL zsh invocations including non-interactive SSH. If using bash over SSH, add the Guix profile to PATH manually:

```bash
export PATH="$HOME/.guix-extra-profiles/core/core/bin:$PATH"
```

## "not owned by stow" after repo rename (.dotfiles -> DotCortex)

If the repo was renamed, all old stow symlinks become foreign (pointing to the old path). Stow reports "existing target is not owned by stow" for every file. Remove dangling symlinks first:

```bash
find ~ -maxdepth 5 -lname "*/.dotfiles/*" -not -path "*/.git/*" -delete
```

Then re-stow. The safe-stow target handles this conflict type automatically with its third sed pattern.

## safe-stow handles three stow conflict message formats

Stow has three different conflict message formats across versions and situations:

1. `existing target is neither a link nor a directory: FILE` (stow <2.4)
2. `cannot stow PKG/FILE over existing target FILE since neither...` (stow 2.4+)
3. `existing target is not owned by stow: FILE` (foreign files/symlinks after repo rename)

The safe-stow target in `loom.org` matches all three with sed patterns, filters out HelmCortex (which is always a user-managed symlink on mounted machines), backs up real files, removes them, then stows. If stow still fails, it auto-retries with `--ignore=HelmCortex`.

## Guix installer fails on non-interactive terminal

The official `guix-install.sh` requires interactive stdin. If running via SSH, CI, or piped input, use the manual install method documented in `INSTALL.sh`.

## Guix installer fails with "Missing commands: daemonize"

On Devuan/sysv-init systems, install `daemonize` first: `sudo apt install daemonize`

## Guix ftpmirror SSL errors

The `ftpmirror.gnu.org` redirector sometimes sends you to mirrors with broken SSL certificates. Use `ftp.gnu.org` directly:

```bash
wget https://ftp.gnu.org/gnu/guix/guix-binary-1.5.0.x86_64-linux.tar.xz
```

## LD_PRELOAD libgtk3-nocsd warning

On systems with `libgtk3-nocsd` in `LD_PRELOAD`, Guix commands emit a warning about being unable to preload it. This is cosmetic — Guix works fine. Unset `LD_PRELOAD` if it bothers you.

## Absolute symlinks in overlay dirs abort stow

If an org file tangles an absolute symlink (e.g. `.config/guix/current -> /var/guix/...`), stow will refuse to manage it. Remove such symlinks from overlay dirs before stowing — they are machine-specific and should not be stow-managed. `INSTALL.sh` auto-cleans these.

## /tmp permissions break tangle AND guix pull

If `/tmp` has restrictive permissions (e.g. `755` instead of `1777`), two things break:

1. **Tangle**: emacs `org-persist` can't create temp directories -> `Permission denied, /tmp/org-persist-`
2. **Guix pull/build**: sandbox can't bind-mount -> `bind: Permission denied`

Fix the root cause: `sudo chmod 1777 /tmp`

Workaround for tangle only: `TMPDIR=~/.cache/tmp make tangle`

## pipefail interaction with grep -v

Under `set -euo pipefail`, `grep -v PATTERN` returns exit code 1 when it filters ALL lines (nothing passes through). This kills the pipeline. Always wrap: `{ grep -v PATTERN || true; }`

## Guix substituter display bug

`guix package` occasionally crashes with `Wrong type argument in position 1: #f` during substitute download progress display. This is a cosmetic bug in `guix/progress.scm`. Retry the command — most substitutes will already be cached so it's fast.
