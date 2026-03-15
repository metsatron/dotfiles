# DotCortex — Literate Dotfiles System

## What This Is

DotCortex is Mètsàtron's declarative, literate, reproducible dotfiles system. Org-mode files are the single source of truth. They tangle into overlay directories which GNU Stow symlinks into `$HOME`.

## Architecture

```
*.org files  →  make tangle  →  overlay dirs  →  make safe-stow  →  $HOME
```

- **Org files** (root level): canonical source for all configs, scripts, manifests
- **Overlay dirs**: `all/` (shared), `linux/`, `debian/`, `devuan/` (sysv-init), `x230/` (X230 ThinkPad), `t480s/` (T480s ThinkPad), `arch/`, `osx/`, `be/`, `navi/`
- **Stow**: symlinks overlay contents into `$HOME`, stacked in priority order
- **Loom**: Guile Scheme control plane (`~/.local/bin/loom`) with 50+ task verbs
- **Loom requires Guix** — it uses Guix's guile interpreter. Without Guix, use `make` targets directly.

## Critical Rules

1. **Never edit tangled output files** — edit the `.org` source and re-tangle. Files inside overlay dirs (`all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`, `be/`, `navi/`, `arch/`, `osx/`) are generated output.
2. **Org files are at repo root** — the overlay dirs contain only tangled output.
3. **Stow target is `$HOME`** — the repo must live at `~/DotCortex`.
4. **`make safe-stow`** backs up existing files before stowing — use it instead of `make stow`.
5. **Follow existing patterns** — new package managers get: `.org` file + SSV manifest + capture/diff/apply/health scripts + `.mk` Makefile fragment + loom verbs in `loom.org`.

## Common Workflows

```bash
# Full rebuild (X230)
cd ~/DotCortex && make tangle && loom stow:x230

# Full rebuild (T480s)
cd ~/DotCortex && make tangle && loom stow:t480s

# Without loom (make targets work without Guix)
make tangle && STOW_PKGS='all linux debian devuan t480s' make safe-stow

# Edit a config
# 1. Find the org source: grep -rn "tangle.*path/to/config" *.org
# 2. Edit the org block
# 3. make tangle && loom stow:t480s (or stow:x230)

# Loom verbs (requires Guix guile)
loom                    # list all verbs
loom guix:apply         # apply Guix manifest
loom flatpak:apply      # apply Flatpak manifest
loom pip:apply          # install pip manifest
loom npm:apply          # install npm manifest
loom stow:x230          # stow X230 overlays (all linux debian x230)
loom stow:t480s         # stow T480s overlays (all linux debian devuan t480s)
loom stow:devuan        # stow shared + linux + devuan only

# Without loom (make targets work without Guix)
make pip-apply
make npm-apply
make safe-stow
```

## Package Manifests

Each package manager has an `.org` file that tangles a manifest (`.ssv`) and helper scripts:

| Manager  | Org File       | Manifest                              | Loom Verbs                        |
|----------|----------------|---------------------------------------|-----------------------------------|
| Guix     | `guix.org`     | `.config/guix/manifests/*.scm`        | `guix:apply`, `guix:pull`         |
| Flatpak  | `flatpak.org`  | `linux/.flatpak/manifest/apps.ssv`    | `flatpak:apply`, `flatpak:diff`   |
| Snap     | `snap.org`     | `all/.snap/manifest/apps.ssv`         | `snap:apply`, `snap:diff`         |
| Pip      | `pip.org`      | `all/.pip/manifest/packages.ssv`      | `pip:apply`, `pip:diff`           |
| NPM      | `npm.org`      | `all/.npm/manifest/global.ssv`        | `npm:apply`, `npm:diff`           |
| Cargo    | `cargo.org`    | `all/.cargo/manifest/crates.ssv`      | `cargo:apply`, `cargo:diff`       |
| AppImage | `appimage.org` | `all/.appimage/inventory/all.ssv`     | `appimage:update`                 |
| Homebrew | `homebrew.org` | `all/.homebrew/manifest/brews.ssv`    | `brew:apply`                      |
| Apps     | `app.org`      | `all/.app/manifest/apps.ssv`          | `app:apply`                       |

### SSV Manifest Format

All manifests use space-separated values with `""` for empty fields:

```
# PKG VERSION EXTRA
litellm "" ""
openai "" ""
```

### Adding a New Package Manager

1. Create `newpkg.org` at repo root
2. Add a manifest SSV block with `:tangle all/.newpkg/manifest/packages.ssv`
3. Add capture/diff/apply/health scripts with `:tangle all/.local/bin/newpkg-*`
4. Add a `.mk` Makefile fragment with `:tangle all/.mk/newpkg.mk`
5. Add `include $(HOME)/DotCortex/all/.mk/newpkg.mk` to the Makefile block in `loom.org`
6. Add loom task verbs to the Scheme control plane in `loom.org`
7. `make tangle` to generate everything

## Key Files

- `Makefile` — build system entry point (tangle, stow, guix-dirs) — **tangled from `loom.org`**, never edit directly
- `loom.org` — control plane, Makefile template, batch helpers
- `shell.org` — bash/zsh rc, exports, aliases, functions, prompt, `.zshenv` (SSH PATH)
- `style.org` — LainCore theme (fonts, colours, GTK, terminal, Emacs)
- `INSTALL.sh` — bootstrap script for fresh machines
- `README.org` — full Org documentation (the original grimoire)

## Bootstrap (Fresh Machine)

```bash
git clone --recursive https://gitlab.com/metsarono/dotfiles.git ~/DotCortex
cd ~/DotCortex && bash INSTALL.sh
```

See `INSTALL.sh` for detailed phase-by-phase documentation including lessons learned on Guix installation, init system differences, and first-tangle bootstrapping.

## Known Gotchas

### Makefile is tangled output — never edit it directly

The Makefile is tangled from `loom.org`. Any direct edits will be overwritten by the next `make tangle`. Always edit the Makefile template block in `loom.org` instead, then re-tangle.

### First tangle fails with "No rule to make target .mk"

The Makefile includes `.mk` fragment files that don't exist until after the first tangle. `INSTALL.sh` handles this by creating empty stubs. If running manually:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

### Loom bootstrap (chicken-and-egg)

`loom` needs `~/.config/maak/maak.scm` (placed by stow) and Guix guile. You CANNOT use `loom stow:x230` for the first stow — use `make safe-stow` directly. `INSTALL.sh` handles this by pre-placing `maak.scm` before stow runs (Phase 5.5).

After the first `make safe-stow`, loom is functional and can be used for all subsequent stow operations.

### Guix emacs not in SSH PATH

On Guix machines, emacs lives at `~/.guix-extra-profiles/core/core/bin/emacs`. It is NOT in the default SSH PATH. The `.zshenv` file (tangled from `shell.org`) sources Guix profiles for ALL zsh invocations including non-interactive SSH. If using bash over SSH, add the Guix profile to PATH manually:

```bash
export PATH="$HOME/.guix-extra-profiles/core/core/bin:$PATH"
```

### "not owned by stow" after repo rename (.dotfiles → DotCortex)

If the repo was renamed, all old stow symlinks become foreign (pointing to the old path). Stow reports "existing target is not owned by stow" for every file. Remove dangling symlinks first:

```bash
find ~ -maxdepth 5 -lname "*/.dotfiles/*" -not -path "*/.git/*" -delete
```

Then re-stow. The safe-stow target handles this conflict type automatically with its third sed pattern.

### safe-stow handles three stow conflict message formats

Stow has three different conflict message formats across versions and situations:

1. `existing target is neither a link nor a directory: FILE` (stow <2.4)
2. `cannot stow PKG/FILE over existing target FILE since neither...` (stow 2.4+)
3. `existing target is not owned by stow: FILE` (foreign files/symlinks after repo rename)

The safe-stow target in `loom.org` matches all three with sed patterns, filters out HelmCortex (which is always a user-managed symlink on mounted machines), backs up real files, removes them, then stows. If stow still fails, it auto-retries with `--ignore=HelmCortex`.

### Guix installer fails on non-interactive terminal

The official `guix-install.sh` requires interactive stdin. If running via SSH, CI, or piped input, use the manual install method documented in `INSTALL.sh`.

### Guix installer fails with "Missing commands: daemonize"

On Devuan/sysv-init systems, install `daemonize` first: `sudo apt install daemonize`

### Guix ftpmirror SSL errors

The `ftpmirror.gnu.org` redirector sometimes sends you to mirrors with broken SSL certificates. Use `ftp.gnu.org` directly:

```bash
wget https://ftp.gnu.org/gnu/guix/guix-binary-1.5.0.x86_64-linux.tar.xz
```

### LD_PRELOAD libgtk3-nocsd warning

On systems with `libgtk3-nocsd` in `LD_PRELOAD`, Guix commands emit a warning about being unable to preload it. This is cosmetic — Guix works fine. Unset `LD_PRELOAD` if it bothers you.

### Absolute symlinks in overlay dirs abort stow

If an org file tangles an absolute symlink (e.g. `.config/guix/current -> /var/guix/...`), stow will refuse to manage it. Remove such symlinks from overlay dirs before stowing — they are machine-specific and should not be stow-managed. `INSTALL.sh` auto-cleans these.

### /tmp permissions break tangle AND guix pull

If `/tmp` has restrictive permissions (e.g. `755` instead of `1777`), two things break:

1. **Tangle**: emacs `org-persist` can't create temp directories → `Permission denied, /tmp/org-persist-`
2. **Guix pull/build**: sandbox can't bind-mount → `bind: Permission denied`

Fix the root cause: `sudo chmod 1777 /tmp`

Workaround for tangle only: `TMPDIR=~/.cache/tmp make tangle`

### pipefail interaction with grep -v

Under `set -euo pipefail`, `grep -v PATTERN` returns exit code 1 when it filters ALL lines (nothing passes through). This kills the pipeline. Always wrap: `{ grep -v PATTERN || true; }`

### Guix substituter display bug

`guix package` occasionally crashes with `Wrong type argument in position 1: #f` during substitute download progress display. This is a cosmetic bug in `guix/progress.scm`. Retry the command — most substitutes will already be cached so it's fast.

## HelmCortex Integration

DotCortex (foundation) and HelmCortex (temple) are fully decoupled. DotCortex does **not** stow any files into HelmCortex — HelmCortex owns all its own configs (`.obsidian/`, `.vscode/`, FORGE/bin scripts, conda configs) directly.

DotCortex's only HelmCortex touchpoint is the shell PATH entry in `shell.org` / `.zshenv` that adds `$HOME/HelmCortex/FORGE/bin` to `$PATH` for tools like `auryn`, `helmcortex-anaconda`, and `claude-code-md-pipeline`.

HelmCortex lives at `~/HelmCortex` (may be a symlink to a mount point like `~/mnt/x230/HelmCortex`).

**Historical note**: HelmCortex configs were previously managed via `helmcortex.org` and stowed from `all/HelmCortex/`. This was decoupled in March 2026. The `style.org` laincore.css tangles directly to `~/HelmCortex/.obsidian/snippets/` (not through stow).

## Multi-Machine Setup (Star Fleet)

DotCortex is designed for deployment across multiple machines:

- **X230** (ThinkPad, Debian/systemd): HelmCortex native, overlays: `all linux debian x230`, loom verb: `loom stow:x230`
- **T480s** (ThinkPad, Devuan/sysv-init): HelmCortex mounted at `~/mnt/x230/`, symlinked to `~/HelmCortex`, overlays: `all linux debian devuan t480s`, loom verb: `loom stow:t480s`
- Future machines: clone DotCortex, run `INSTALL.sh`, done

### Overlay scoping

- `all/` — cross-platform (works on Linux, macOS, etc)
- `linux/` — Linux-only (Guix is Linux-only, so `host-wrap` lives here)
- `debian/` — Debian-family shared (apt/nala packages)
- `devuan/` — sysv-init shared (non-systemd daemons, desktop launchers for XFCE panel scripts)
- `x230/` — X230-specific (earlyoom, neofetch/fastfetch configs, GTK settings, wezterm, systemd services)
- `t480s/` — T480s-specific (future machine-specific configs)

### .zshenv for SSH PATH

The `.zshenv` file (tangled from `shell.org`) sources Guix profiles for ALL zsh invocations (login, interactive, scripts, SSH). This ensures `emacs`, `nvim`, `guile`, and other Guix tools are available over SSH without manual PATH setup.

## When Working on DotCortex

- Always edit `.org` source, never tangled output
- The Makefile is tangled from `loom.org` — edit `loom.org`, not Makefile
- Test with `make tangle` before stowing
- Use `make preview-stow` to dry-run before applying
- After adding new package manager support, add loom verbs AND make targets
- When searching for a tool, check Guix profiles (`~/.guix-extra-profiles/core/core/bin/`) before assuming it's not installed
