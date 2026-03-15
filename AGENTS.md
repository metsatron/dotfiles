# DotCortex — Agent Instructions

## What This Is

DotCortex is a literate, declarative, reproducible dotfiles system. Org-mode files at the repo root are the single source of truth. They tangle into overlay directories which GNU Stow symlinks into `$HOME`.

See `CLAUDE.md` for full architecture details, common workflows, and package manifest reference.

## Critical Rules

1. **Never edit tangled output** — files inside `all/`, `linux/`, `debian/`, `think/`, `be/`, `navi/`, `arch/`, `osx/` are generated. Edit the `.org` source at repo root instead.
2. **Org files are canonical** — every config, script, and manifest is defined inside an org code block with a `:tangle` target.
3. **Stow target is `$HOME`** — the repo lives at `~/DotCortex`.
4. **Use `make safe-stow`** — it backs up existing files before stowing. Never use plain `stow` directly.
5. **Follow existing patterns** — new package managers get: `.org` file + SSV manifest + capture/diff/apply/health scripts + `.mk` Makefile fragment + loom verbs.

## Build & Apply

```bash
cd ~/DotCortex
make tangle                                          # org → overlay files
make safe-stow STOW_PKGS="all linux debian think"   # stow with backup
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

### Guix on Non-systemd Systems (Devuan, sysv-init)

The official Guix installer (`guix-install.sh`) requires interactive stdin and will fail when piped or run non-interactively. On sysv-init systems:

1. Install `daemonize` first: `sudo apt-get install -y daemonize`
2. Use the manual install method documented in `INSTALL.sh` (download tarball, extract, create build users, write init script)
3. The `ftpmirror.gnu.org` redirector sometimes has broken SSL — use `ftp.gnu.org` directly

### LD_PRELOAD Warning

On systems with `libgtk3-nocsd` in `LD_PRELOAD`, Guix commands emit a harmless warning. Ignore it or `unset LD_PRELOAD`.

### Stow Conflicts

- **safe-stow sed pattern**: Stow 2.4+ changed message format. The safe-stow target in `loom.org` handles both old and new formats. If backup isn't working, check the sed patterns.
- **HelmCortex symlink**: On mounted machines where `~/HelmCortex` is a symlink, stow reports "not owned by stow". Use `--ignore='HelmCortex'`. The safe-stow target auto-retries with this flag.
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

DotCortex coexists with HelmCortex (knowledge/project system) at `~/HelmCortex`. Shell PATH entries include `$HOME/HelmCortex/FORGE/bin` for tools like `auryn` (brain CLI) and `claude-code-md-pipeline`.

On multi-machine setups, HelmCortex may be mounted (e.g., `~/mnt/x230/HelmCortex`) and symlinked to `~/HelmCortex`.

## Multi-Machine Setup (Star Fleet)

- **X230** (ThinkPad): HelmCortex native, overlays: `all linux debian think`
- **T480s** (ThinkPad): HelmCortex mounted at `~/mnt/x230/`, symlinked to `~/HelmCortex`, overlays: `all linux debian`
- Future machines: clone DotCortex, run `INSTALL.sh`, done

The overlay system means machine-specific configs go in `think/` (or a new overlay) while shared configs live in `all/`.
