---
name: dotcortex-bootstrap
description: Bootstrap DotCortex on fresh or recovering machines by following INSTALL.sh, handling first-tangle and first-stow constraints, and navigating Guix and init-system gotchas safely.
---

# DotCortex Bootstrap Operations for OpenCode

Use this skill when the task is about first install, machine provisioning, recovery after a broken setup, or bringing a new machine into a working DotCortex state.

## Use This Skill For

- fresh machine setup
- first clone and initial DotCortex install
- recovery after failed tangle, stow, or bootstrap
- Guix bootstrap constraints on Debian or Devuan systems
- first-time Loom enablement
- machine-specific bootstrap guidance for `x230`, `t480s`, or shared `devuan` flows

## Do Not Use This Skill For

- routine package manifest edits
- ordinary config changes after the machine is already healthy
- broad repo development unrelated to machine provisioning

Use `dotcortex-loom` for normal operating tasks and `dotcortex-package-manifests` for package list changes.

## Critical Safety Rules

1. Follow `INSTALL.sh` as the bootstrap entry point unless there is a clear reason to do a manual repair.
2. Never edit tangled overlay output to fix bootstrap issues; fix the root `.org` source or bootstrap process.
3. Never edit `Makefile` directly; it is tangled from `loom.org`.
4. Use `make safe-stow` for the first stow.
5. Do not assume Loom works before `maak.scm` is in place and Guix's `guile` is available.

## Bootstrap Entry Point

Standard flow:

```bash
git clone --recursive https://gitlab.com/metsarono/dotfiles.git ~/DotCortex
cd ~/DotCortex && bash INSTALL.sh
```

Assume the repo path is `~/DotCortex`.

## Preflight Checks

Before recommending commands, check:

- is the repo actually at `~/DotCortex`
- is this a fresh machine or a repair scenario
- is the system Debian, Devuan, or something else
- is Guix already installed
- are key Guix tools only available in `~/.guix-extra-profiles/core/core/bin/`
- is `/tmp` configured correctly with mode `1777`

## First-Tangle Rule

The first `make tangle` can fail because `.mk` fragments do not exist yet.

If needed, create stubs first:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

## First-Stow Rule

For the first stow on a fresh machine:

```bash
cd ~/DotCortex
make safe-stow
```

Do not rely on Loom yet. Loom needs `~/.config/maak/maak.scm` from stow and Guix's `guile`.

## Machine-Specific Apply Guidance

After bootstrap is healthy and Loom is available:

```bash
loom stow:x230
loom stow:t480s
loom stow:devuan
```

Overlay expectations:

- `x230` -> `all linux debian x230`
- `t480s` -> `all linux debian devuan t480s`
- `devuan` -> shared `all linux devuan`

## Guix Guidance

### Guix Not in PATH

Tools like `emacs`, `guile`, `nvim`, and `zsh` may live in:

```bash
~/.guix-extra-profiles/core/core/bin/
```

For bash SSH sessions, a temporary fix may be:

```bash
export PATH="$HOME/.guix-extra-profiles/core/core/bin:$PATH"
```

### Devuan or sysv-init Systems

The official `guix-install.sh` is not reliable in non-interactive or sysv-init contexts.

Important notes:
- install `daemonize` first when needed
- use the manual install path documented in `INSTALL.sh`
- prefer `ftp.gnu.org` if `ftpmirror.gnu.org` has SSL issues

## Common Recovery Cases

### `/tmp` Permissions Broken

Symptoms:
- org persist temp directory failures during tangle
- Guix sandbox bind errors during pull or build

Fix:

```bash
sudo chmod 1777 /tmp
```

Tangle-only workaround:

```bash
TMPDIR=~/.cache/tmp make tangle
```

### Old `.dotfiles` Symlinks After Rename

If older symlinks still point at a previous repo path, stow may report `not owned by stow`.

Cleanup command:

```bash
find ~ -maxdepth 5 -lname "*/.dotfiles/*" -not -path "*/.git/*" -delete
```

Then retry safe stow.

### Absolute Symlinks in Overlay Output

Absolute symlinks inside overlay output can cause stow to abort. These are machine-specific and should not be stow-managed.

### LD_PRELOAD Warning

If `libgtk3-nocsd` appears in `LD_PRELOAD`, Guix may print cosmetic warnings. This is usually harmless.

## Validation After Bootstrap

Minimum validation sequence:

```bash
cd ~/DotCortex
make tangle
make preview-stow
```

When Loom is working:

```bash
loom
loom pip:health
loom npm:health
```

Use machine-specific stow verbs for later updates instead of repeating full bootstrap.

## Reporting Expectations

When finishing a bootstrap task:

- say whether the system is fresh install or repair
- name any commands run from `INSTALL.sh`, `make tangle`, `make safe-stow`, or Loom
- call out whether `.mk` stubs were needed
- mention any Guix, init-system, or PATH constraints
- mention whether the machine is targeting `x230`, `t480s`, or shared `devuan`
