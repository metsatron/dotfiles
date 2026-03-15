# DotCortex — Literate Dotfiles System

## What This Is

DotCortex is Mètsàtron's declarative, literate, reproducible dotfiles system. Org-mode files are the single source of truth. They tangle into overlay directories (`all/`, `linux/`, `debian/`, `think/`) which GNU Stow symlinks into `$HOME`.

## Architecture

```
*.org files  →  make tangle  →  overlay dirs  →  make safe-stow  →  $HOME
```

- **Org files** (root level): canonical source for all configs, scripts, manifests
- **Overlay dirs**: `all/` (shared), `linux/`, `debian/`, `arch/`, `osx/`, `think/` (hardware), `be/`, `navi/`
- **Stow**: symlinks overlay contents into `$HOME`, stacked in priority order
- **Loom**: Guile Scheme control plane (`~/.local/bin/loom`) with 50+ task verbs
- **Loom requires Guix** — it uses Guix's guile interpreter. Without Guix, use `make` targets directly.

## Critical Rules

1. **Never edit tangled output files** — edit the `.org` source and re-tangle. Files inside `all/`, `linux/`, `debian/`, `think/`, `be/`, `navi/`, `arch/`, `osx/` are generated output.
2. **Org files are at repo root** — the overlay dirs contain only tangled output.
3. **Stow target is `$HOME`** — the repo must live at `~/DotCortex`.
4. **`make safe-stow`** backs up existing files before stowing — use it instead of `make stow`.
5. **Follow existing patterns** — new package managers get: `.org` file + SSV manifest + capture/diff/apply/health scripts + `.mk` Makefile fragment + loom verbs in `loom.org`.

## Common Workflows

```bash
# Full rebuild
cd ~/DotCortex && make tangle && make safe-stow STOW_PKGS="all linux debian think"

# Edit a config
# 1. Find the org source: grep -rn "tangle.*path/to/config" *.org
# 2. Edit the org block
# 3. make tangle && make safe-stow

# Loom verbs (requires Guix guile)
loom                    # list all verbs
loom guix:apply         # apply Guix manifest
loom flatpak:apply      # apply Flatpak manifest
loom pip:apply          # install pip manifest
loom npm:apply          # install npm manifest
loom stow               # stow all overlays

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

- `Makefile` — build system entry point (tangle, stow, guix-dirs)
- `loom.org` — control plane, Makefile template, batch helpers
- `shell.org` — bash/zsh rc, exports, aliases, functions, prompt
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

### First tangle fails with "No rule to make target .mk"

The Makefile includes `.mk` fragment files that don't exist until after the first tangle. `INSTALL.sh` handles this by creating empty stubs. If running manually:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

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

### safe-stow sed pattern doesn't match (stow 2.4+)

Stow 2.4 changed its conflict message format. The old format was:

```
existing target is neither a link nor a directory: .bashrc
```

The new format is:

```
cannot stow DotCortex/all/.bashrc over existing target .bashrc since neither a link nor a directory
```

The safe-stow target in `loom.org` handles both patterns. If you see safe-stow failing to backup conflicting files, check the sed patterns match your stow version.

### Stow fails with "existing target is not owned by stow: HelmCortex"

On machines where `~/HelmCortex` is a user-managed symlink (e.g. T480s mount), stow cannot merge into it. Use `--ignore='HelmCortex'` on those machines. On the X230 where `~/HelmCortex` is a real directory, stow works fine. The safe-stow target auto-retries with `--ignore=HelmCortex` on failure.

### Absolute symlinks in overlay dirs abort stow

If an org file tangles an absolute symlink (e.g. `.config/guix/current -> /var/guix/...`), stow will refuse to manage it. Remove such symlinks from overlay dirs before stowing — they are machine-specific and should not be stow-managed. `INSTALL.sh` auto-cleans these.

### Tangle fails with "Permission denied, /tmp/org-persist-"

If `/tmp` has restrictive permissions (e.g. `755` instead of `1777`), emacs batch-mode tangle fails because `org-persist` can't create temp directories. Fix with:

```bash
TMPDIR=~/.cache/tmp make tangle
```

Or fix `/tmp` permissions: `sudo chmod 1777 /tmp`

## HelmCortex Integration

DotCortex (foundation) and HelmCortex (temple) are fully decoupled. DotCortex does **not** stow any files into HelmCortex — HelmCortex owns all its own configs (`.obsidian/`, `.vscode/`, FORGE/bin scripts, conda configs) directly.

DotCortex's only HelmCortex touchpoint is the shell PATH entry in `shell.org` that adds `$HOME/HelmCortex/FORGE/bin` to `$PATH` for tools like `auryn`, `helmcortex-anaconda`, and `claude-code-md-pipeline`.

HelmCortex lives at `~/HelmCortex` (may be a symlink to a mount point like `~/mnt/x230/HelmCortex`).

**Historical note**: HelmCortex configs were previously managed via `helmcortex.org` and stowed from `all/HelmCortex/`. This was decoupled in March 2026. The legacy org file is archived at `HelmCortex/ROOTS/DotRoot/helmcortex.org`.

## Multi-Machine Setup (Star Fleet)

DotCortex is designed for deployment across multiple machines:

- **X230** (ThinkPad): HelmCortex native, FORGE/bin on PATH, overlays: `all linux debian think`
- **T480s** (ThinkPad): HelmCortex mounted at `~/mnt/x230/`, symlinked to `~/HelmCortex`, overlays: `all linux debian`
- Future machines: clone DotCortex, run `INSTALL.sh`, done

The overlay system means machine-specific configs go in `think/` (or a new overlay) while shared configs live in `all/`.

## When Working on DotCortex

- Use `@dotcortex-loom` skill for loom verb operations
- Always edit `.org` source, never tangled output
- Test with `make tangle` before stowing
- Use `make preview-stow` to dry-run before applying
- After adding new package manager support, add loom verbs AND make targets
