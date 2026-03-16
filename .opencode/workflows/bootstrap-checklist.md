# Bootstrap Checklist

Use this when helping with a fresh DotCortex machine.

## Base Flow

```bash
git clone --recursive https://gitlab.com/metsarono/dotfiles.git ~/DotCortex
cd ~/DotCortex && bash INSTALL.sh
```

## Preflight Checks

- Confirm the repo is at `~/DotCortex`
- Check whether Guix is already available
- Check whether the machine is Debian, Devuan, or another target
- Remember that Guix tools may live under `~/.guix-extra-profiles/core/core/bin/`

## First-Tangle Requirement

If `.mk` fragments are missing, create stubs before tangling:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

## First-Stow Rule

- Use `make safe-stow` for the first stow
- Do not rely on Loom until `maak.scm` is in place and Guix's `guile` is available

## Common Gotchas

- `/tmp` must usually be `1777`
- `daemonize` is needed for manual Guix install on Devuan or sysv-init systems
- `ftpmirror.gnu.org` may have SSL issues; prefer `ftp.gnu.org`
- `LD_PRELOAD` warnings from `libgtk3-nocsd` are usually cosmetic
- old `.dotfiles` symlinks can break stow after repo rename

## After Bootstrap

- Run `loom` to inspect available verbs when Loom is working
- Verify package managers with commands like `loom pip:health` and `loom npm:health`
- Use machine-specific stow verbs for future updates instead of repeating bootstrap
