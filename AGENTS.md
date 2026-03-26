# DotCortex — Agent Instructions

## What This Is

DotCortex is a literate, declarative, reproducible dotfiles system. Org-mode files at the repo root are the single source of truth. They tangle into overlay directories which GNU Stow symlinks into `$HOME`.

See `CLAUDE.md` for full architecture details, common workflows, and package manifest reference.

## Critical Rules

1. **Never touch any `.claude` path or `CLAUDE.md` unless the user explicitly names that exact path for direct modification** — all `.claude` directories and files anywhere, plus `CLAUDE.md`, are Claude-owned, must be treated as read-only reference material by default, and must never be created, edited, deleted, moved, symlinked, or synced as part of DotCortex/OpenCode work.
2. **Never edit tangled output** — files inside `all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`, `be/`, `navi/`, `arch/`, `osx/` are generated. Edit the `.org` source at repo root instead.
3. **Never edit the Makefile directly** — it is tangled from `loom.org`. Edit `loom.org` instead, then `make tangle`.
4. **Org files are canonical** — every config, script, and manifest is defined inside an org code block with a `:tangle` target.
5. **Stow target is `$HOME`** — the repo lives at `~/DotCortex`.
6. **Use `make safe-stow`** — it backs up existing files before stowing. Never use plain `stow` directly.
7. **Follow existing patterns** — new package managers get: `.org` file + SSV manifest + capture/diff/apply/health scripts + `.mk` Makefile fragment + loom verbs.
8. **Check Guix profiles before assuming tools aren't installed** — emacs, nvim, zsh, guile etc live at `~/.guix-extra-profiles/core/core/bin/`, not in system PATH.

## Build & Apply

```bash
cd ~/DotCortex
make tangle                                          # org → overlay files

# With loom (requires Guix guile + stowed maak.scm)
loom stow:x230                                       # X230: all linux debian x230
loom stow:t480s                                      # T480s: all linux debian devuan t480s
loom stow:devuan                                     # shared: all linux devuan

# Without loom (first stow, or systems without Guix)
STOW_PKGS='all linux debian devuan t480s' make safe-stow
```

## Bootstrap (Fresh Machine)

```bash
cd ~/DotCortex && bash INSTALL.sh
```

See `INSTALL.sh` for the full phase-by-phase bootstrap process. Key things to know:

### First Tangle Will Fail Without Stubs

The Makefile includes `.mk` fragment files that don't exist until after the first tangle. You must create empty stubs first:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

### Loom Bootstrap (Chicken-and-Egg)

`loom` needs `~/.config/maak/maak.scm` (placed by stow) and Guix guile. You CANNOT use `loom stow:x230` for the first stow — use `make safe-stow` directly. `INSTALL.sh` handles this by pre-placing maak.scm before stow runs.

### Guix Emacs Not in SSH PATH

On Guix machines, emacs lives at `~/.guix-extra-profiles/core/core/bin/emacs`. It is NOT in the default SSH PATH. The `.zshenv` sources Guix profiles for all zsh invocations. For bash SSH sessions:

```bash
export PATH="$HOME/.guix-extra-profiles/core/core/bin:$PATH"
```

### Guix on Non-systemd Systems (Devuan, sysv-init)

The official Guix installer (`guix-install.sh`) requires interactive stdin and will fail when piped or run non-interactively. On sysv-init systems:

1. Install `daemonize` first: `sudo apt-get install -y daemonize`
2. Use the manual install method documented in `INSTALL.sh` (download tarball, extract, create build users, write init script)
3. The `ftpmirror.gnu.org` redirector sometimes has broken SSL — use `ftp.gnu.org` directly

### LD_PRELOAD Warning

On systems with `libgtk3-nocsd` in `LD_PRELOAD`, Guix commands emit a harmless warning. Ignore it or `unset LD_PRELOAD`.

### Stow Conflicts

The safe-stow target handles three conflict message formats:

1. `existing target is neither a link nor a directory: FILE` (stow <2.4)
2. `cannot stow PKG/FILE over existing target FILE since neither...` (stow 2.4+)
3. `existing target is not owned by stow: FILE` (foreign files/symlinks after repo rename)

It filters out HelmCortex (user-managed symlink on mounted machines), backs up real files, then stows. On failure, auto-retries with `--ignore=HelmCortex`.

- **"not owned by stow" after repo rename**: If the repo was renamed (`.dotfiles` → `DotCortex`), all old stow symlinks become foreign. Remove dangling symlinks first: `find ~ -maxdepth 5 -lname "*/.dotfiles/*" -not -path "*/.git/*" -delete`, then re-stow.
- **Absolute symlinks**: Org files that tangle absolute symlinks (e.g. `.config/guix/current`) will cause stow to abort. Remove them from overlay dirs — they're machine-specific.

## Package Manifests

| Manager  | Org File       | Loom Verbs                      |
|----------|----------------|---------------------------------|
| Pip      | `pip.org`      | `pip:apply`, `pip:diff`         |
| NPM      | `npm.org`      | `npm:apply`, `npm:diff`         |
| Guix     | `guix.org`     | `guix:apply`, `guix:pull`       |
| Flatpak  | `flatpak.org`  | `flatpak:apply`, `flatpak:diff` |
| Snap     | `snap.org`     | `snap:apply`, `snap:diff`       |
| Cargo    | `cargo.org`    | `cargo:apply`, `cargo:diff`     |
| AppImage | `appimage.org` | `appimage:update`               |
| Homebrew | `homebrew.org` | `brew:apply`                    |
| Apps     | `app.org`      | `app:apply`                     |

### Adding a New Package Manager

1. Create `newpkg.org` at repo root
2. Add a manifest SSV block with `:tangle all/.newpkg/manifest/packages.ssv`
3. Add capture/diff/apply/health scripts with `:tangle all/.local/bin/newpkg-*`
4. Add a `.mk` Makefile fragment with `:tangle all/.mk/newpkg.mk`
5. Add `include $(HOME)/DotCortex/all/.mk/newpkg.mk` to the Makefile block in `loom.org`
6. Add loom task verbs to the Scheme control plane in `loom.org`
7. `make tangle` to generate everything

### SSV Manifest Format

All manifests use space-separated values with `""` for empty fields:

```
# PKG VERSION EXTRA
litellm "" ""
openai "" ""
```

## Finding What Owns a Config

```bash
grep -rn "tangle.*path/to/config" *.org
```

## Loom (Control Plane)

Loom is a Guile Scheme CLI (`~/.local/bin/loom`) that wraps make targets and adds batch operations. **Loom requires Guix** — it uses Guix's guile interpreter. Without Guix, use `make` targets directly:

```bash
# With loom (requires Guix guile)
loom pip:apply
loom flatpak:diff

# Without loom (make targets work anywhere)
make pip-apply
make npm-apply
make safe-stow
```

## HelmCortex Integration

DotCortex (foundation) and HelmCortex (temple) are fully decoupled. DotCortex does **not** stow any files into HelmCortex. HelmCortex owns all its own configs directly (`.obsidian/`, `.vscode/`, FORGE/bin scripts, conda configs).

DotCortex's only touchpoint is the shell PATH entry (in `.zshenv` and `.zshrc`) adding `$HOME/HelmCortex/FORGE/bin` for tools like `auryn`, `helmcortex-anaconda`, and `claude-code-md-pipeline`.

On multi-machine setups, HelmCortex may be mounted (e.g., `~/mnt/x230/HelmCortex`) and symlinked to `~/HelmCortex`.

## Multi-Machine Setup (Star Fleet)

- **X230** (ThinkPad, Debian/systemd): HelmCortex native, overlays: `all linux debian x230`, verb: `loom stow:x230`
- **T480s** (ThinkPad, Devuan/sysv-init): HelmCortex mounted, symlinked, overlays: `all linux debian devuan t480s`, verb: `loom stow:t480s`
- Future machines: clone DotCortex, run `INSTALL.sh`, done

### Overlay Scoping

- `all/` — cross-platform shared
- `linux/` — Linux-only (host-wrap, Guix wrappers)
- `debian/` — Debian-family (apt/nala)
- `devuan/` — sysv-init shared (non-systemd daemons, XFCE panel launchers)
- `x230/` — X230-specific (earlyoom, neofetch, fastfetch, GTK, wezterm, systemd services)
- `t480s/` — T480s-specific (future per-machine configs)
