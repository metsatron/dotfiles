# DotCortex — Agent Instructions

This file is for OpenCode, Codex, and other non-Claude agents working in this repository.
Claude Code users: `CLAUDE.md` carries the harness-specific Claude guidance.
Source of truth for both files: `agents.org`.


## What This Is

DotCortex is Mètsàtron's declarative, literate, reproducible dotfiles system. Org-mode files are the single source of truth. They tangle into overlay directories which GNU Stow symlinks into `$HOME`.

## Architecture

```
*.org files  ->  tangle  ->  overlay dirs  ->  loom stow  ->  $HOME
```

- **Org files** (root level): canonical source for all configs, scripts, manifests
- **Overlay dirs**: `all/` (shared), `linux/`, `debian/`, `devuan/` (sysv-init), `x230/` (X230 ThinkPad), `t480s/` (T480s ThinkPad), `arch/`, `osx/`, `be/`, `navi/`
- **Stow**: symlinks overlay contents into `$HOME`, stacked in priority order
- **Loom**: Guile Scheme control plane (`~/.local/bin/loom`) with 50+ task verbs -- requires Guix guile. Without Guix, use `make` targets directly.

## Critical Rules

1. **Never edit tangled output** -- files inside overlay dirs (`all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`, `be/`, `navi/`, `arch/`, `osx/`) are generated. Edit the `.org` source at repo root instead.
2. **Never edit the Makefile directly** -- it is tangled from `loom.org`. Edit `loom.org` instead.
3. **Org files are canonical** -- every config, script, and manifest is defined inside an org code block with a `:tangle` target.
4. **Stow target is `$HOME`** -- the repo lives at `~/DotCortex`.
5. **Stow via loom** -- use `loom stow:x230` or `loom stow:t480s` for normal operations. `make safe-stow` is only for first-time bootstrap before loom is functional, or when Guix is unavailable. Never use plain `stow` directly.
6. **Follow existing patterns** -- new package managers get: `.org` file + SSV manifest + capture/diff/apply/health scripts + `.mk` Makefile fragment + loom verbs in `loom.org`.
6a. **Never install packages directly** -- never run `pip install`, `guix install`, `flatpak install`, `cargo install`, `npm install -g`, or any package manager CLI directly. Always: (1) edit the relevant `.org` file (e.g. `pip.org`, `guix.org`), (2) add the package to the manifest SSV block, (3) `tangle-one <file>.org`, (4) run the appropriate `loom <mgr>:apply`. The `.org` files are the single source of truth; bypassing them leaves the system in an undeclared state.
7. **Check Guix profiles before assuming tools aren't installed** -- emacs, nvim, zsh, guile, and other Guix tools live at `~/.guix-extra-profiles/core/core/bin/`, not in system PATH.
8. **All agent work lives in `.org` files** -- skills, hooks, plugins, custom instructions, and settings are authored in org source at repo root and emitted by tangle. Never write directly to harness directories. This includes:
   - New skills: add to `skills.org` with the correct tangle target(s)
   - New hooks or settings: `hooks.org`
   - New Claude plugins: `hooks.org` (plugins.ssv + settings.json)
   - New OpenCode plugins: `npm.org` (bun install) and `hooks.org` (opencode config block)
   - New custom instructions: `agents.org` (this file)
9. **Skills over commands** -- skills are universal across harnesses; harness-specific commands are not portable. Add new agent capabilities as skills in `skills.org`, not as commands.
10. **Never commit from a dirty tracked worktree** -- if `git diff --name-only` shows tracked unstaged changes, stop. Do not commit "just your files" and leave the rest dirty. Split the work intentionally or ask.
10a. **WIP staging / rollback checkpoint law** -- before editing any source-controlled file, establish a reversal point. First run the repo git status. If the target file already has unstaged changes, stage that exact path before editing so the pre-edit state is recoverable from the index. If creating a new source file, stage that exact new path immediately after creation before continuing. For destructive edits, broad rewrites, generated-output sweeps, moves, deletes, or cross-repo source changes, create a narrow `wip: checkpoint before <description>` commit covering the exact affected paths before proceeding. Checkpoint commits are standing-authorized for rollback safety, but must never include unrelated dirty work.
11. **Never commit generated output without canonical source** -- if `all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`, `AGENTS.md`, `CLAUDE.md`, or `Makefile` changed, the corresponding `.org` source must be included in the same commit.
12. **Commit verified work via `/commit`; never push without explicit instruction** -- after useful verified work, commit via the `/commit` skill (which emits the post-commit sync reminder). Do not push or pull between machines unless explicitly asked — pushing triggers multi-machine sync. Stage only intended files; never commit unrelated tracked-file dirt.
12a. **Never run `git pull` on a remote machine without explicit per-machine instruction** -- `git pull` on a remote machine via SSH is as destructive as `git push`. It can silently overwrite uncommitted working state if the incoming changes don't conflict (git fast-forward succeeds even with an otherwise-dirty tree). Never chain `git pull && loom stow:X` on a remote unless the user has explicitly said "pull and stow on X". The correct sync flow is: commit locally → push (with explicit permission) → user pulls on each other machine themselves. Use `dotcortex-pull` for any pull that must be automated — it checks for dirty state first and aborts.
12b. **Never walk past a dirty worktree** -- when `git status` reveals dirty tracked files on any machine (local or remote), stop and assess them. Group them by work/scope, determine what they belong to, and handle them explicitly: commit what is ready, stash what is in-flight, or flag what needs investigation. Do not proceed with unrelated work and leave the mess for later. A dirty worktree is someone's in-progress work — treat it with respect.
13. **Cross-machine sync is explicit** -- for work that must exist on T480s, T480, X230, and S24, use one canonical upstream, `git pull --ff-only` before editing on a machine, and push immediately after an approved commit. Uncommitted work on one machine is not synchronization.
14. **Operate on the target repo root** -- when tangling or running git in mounted/mirrored checkouts, target the actual repo containing the file, not an assumed `~/DotCortex` path. Never assume the local machine repo is the intended target.
15. **"Take care of it" means preserve intent** -- when the user says to "take care of it" about a staged or tracked change, stage and commit the current intended content unless the user explicitly asks for source edits. Do not delete, revert, or silently rewrite it. If a plan was already proposed, "take care of it" means execute that plan.

16. **Change Safety Protocol** -- When editing any file, especially config files:
    - **Read first** -- Always read the full file before making changes. Do not edit a file you have not read completely.
    - **Check file state before touching** -- Use `ls -la` or `stat` to verify the file exists and its current timestamp. Never assume a file is in an expected state.
    - **Checkpoint destructive ops** -- Before making destructive edits to a config file (rewrite, revert, restore from backup), make a timestamped backup: `cp file file.backup-$(date +%Y%m%d-%H%M%S)`.
    - **Never revert to old backup without permission** -- If something goes wrong, do NOT grab an old backup without explicit user confirmation. Ask first.
    - **Stop on edit failure** -- If an edit goes wrong (tool error, file corrupted, structure broken), STOP immediately. Do not continue editing to "fix it". Call `reflect` or ask the user what to do.
    - **No panic edits** -- If you made a mistake, do NOT rush to fix it. Embarrassment and urgency cause more damage. Pause, think, then proceed carefully.
    - **Verify incrementally** -- After each edit, verify the file is in the expected state with `head` or `tail`. If something looks wrong, stop.
    - **Restore is destruction** -- Restoring a file overwrites current state with older state. This is always destructive. Require explicit permission before restoring any file, especially non-DotCortex config files in `~/.hermes/`, `~/.config/`, etc.

17. **TaskHandoff Protocol** -- When planning work for executor agents (Codex, Antigravity, Hermes,
    or any cloud substrate), emit a structured =TaskHandoff= JSON object rather than prose prompts
    or narrative instructions. Schema defined at =HelmCortex/FORGE/brain/helmcortex/AGENTS.md= →
    TaskHandoff Protocol section. Key constraints: paths must be verified against live harness (never
    invented); =allow_git= field controls git permissions for the receiving agent; =NEXUS/= and =LOGS/=
    are forbidden by default. Never emit essays, long explanations, or unverified path hierarchies
    between agent handoffs.

18. **Colemak-NEIO Interaction Law** -- All interactive terminal tools and TUIs built for this
    system must not assume QWERTY/Vim movement keys. Mètsàtron uses **Colemak-NEIO**. Default
    directional movement bindings for any new TUI or interactive script:
    - `n` = left / back / previous / close modal
    - `e` = down / next row
    - `i` = up / previous row
    - `o` = right / open / confirm / enter column
    Additional constraints:
    - `h` means find/search-next in Colemak-NEIO — never use it as "left"
    - `k` means insert — never use it as "up"
    - `l` means newline/open-line — never use it as "right"
    - Never use `h/j/k/l` as the primary movement contract in any TUI
    - Never remap or steal `u/U` or `i/I` for directional movement without explicit instruction
    - Every important action must have a mnemonic letter binding alongside any F-key
    - Vim-style `j/k` may only exist as optional compatibility aliases, never as the
      primary documented bindings

19. **Git Topology Law — EXTREME WarMapCodex VIOLATION** -- The canonical branch is =master=.
    There is no =main=. There will never be a =main=.
    - Referencing =main= as a branch name — in commands, scripts, documentation, instructions,
      or reasoning — is an **EXTREME VIOLATION OF THE WarMapCodex**.
    - Claude Code's =gitStatus= injection may erroneously label the default branch as =main=
      -- ignore it. Run =git branch= to know the truth.
    - =git log main..HEAD=, =git diff main=, =git merge main=, =git checkout main= -- all
      forbidden. Substitute =master= unconditionally.
    - If a subagent, tool, or template defaults to =main=, correct it immediately and flag
      the source.

20. **Private Mutable App Config Boundary** -- DotCortex is public, declarative source. It must
    not own whole mutable GUI/app config trees that contain tokens, browser caches, machine state,
    local databases, cookies, or UI-written runtime settings.
    - Private mutable app config directories belong in `~/HelmCortex/NEXUS/stow/` and are
      deployed with `helmstow`, not tangled or stowed from DotCortex.
    - DotCortex may own public launchers, package manifests, wrappers, and small token-free text
      defaults, but only when the source is genuinely declarative and safe for a public repo.
    - If an app writes secrets into its config directory, move that directory out of DotCortex
      entirely before adding templates, migrations, ignore rules, or abstractions.
    - Never solve a secret-bearing config problem by keeping the live directory in `all/` with
      extra `.gitignore` rules. Move ownership to HelmCortex first, then keep only the DotCortex
      bits the user actually asked to manage.

21. **No network addresses in DotCortex** -- IP addresses (LAN, Tailscale, public), hostname→IP
    mappings, and port numbers that expose network topology must never appear in any tangled org
    source block or overlay file. DotCortex is a public repo — network topology is machine-local.
    - For scripts that need IPs: use an env file pattern — tangle a =*.env.template= with blank
      placeholder values; actual IPs live in a machine-local =*.env= that is never committed.
    - SSH config with fleet hostnames, IPs, or ports belongs in a machine-local file written
      directly to the target machine, not tangled from DotCortex source.
    - If you are about to write any IP address into an org tangle block, stop immediately and
      use the env file pattern instead. No exceptions.

22. **Agent Capability Categories** -- agents and AI-adjacent services are not all the same
    shape. Every agent/service belongs to exactly one category, and its bootstrap follows
    that category's pattern. Do not give a Category A service Category B powers.
    - **Category A — containerized keyless API services**: API-backed routing/serving with no
      filesystem authority. Pattern: no SSH keys, no human home mount, no repo checkout, no
      agent CLIs, no ssh-agent socket, no Docker socket, no broad host mounts; non-root,
      dropped capabilities, explicit env allowlist (no silent inheritance from login shells),
      hash-locked dependencies, loopback-only binding unless explicitly changed; unsupported
      routes fail loud — never silent fallback to host behaviour.
    - **Category B — host CLI agents**: interactive agents that genuinely need toolchains,
      repo work, or supervised escalation. Per-agent Unix users with their own substrates
      (shell basics, package profiles, npm prefix / pipx under the agent's own home, git
      config, controlled repo access). Never assume an agent user can reuse the human
      operator's tools or home.
    - **Category C — persistent narrow agents**: 24/7 daemons. Own users, sudo limited to
      enumerated root-owned wrappers, no human keys, no backup-destruction capability.
    - **Category D — client-side agents**: scoped to one client environment, per-client
      revocable identities, never trusted with personal-mesh credentials.
    - Container env files are explicit allowlists: no broad =.env= import without filtering.
      Docker env-files take values literally — strip =export= prefixes and surrounding quotes
      when deriving from shell-sourced env files.

## Agent Config Scoping

Harness-exclusive config lives in its own directory. Nothing crosses these boundaries uninvited:

| Path | Harness | Notes |
|------|---------|-------|
| `.claude/` | Claude Code only | `CLAUDE.md`, settings, skills, hooks |
| `.opencode/` | OpenCode only | Plugins, bun packages, OpenCode-specific skills |
| `.codex/` | Codex only | Codex-specific config and skills |
| `.agents/` | Universal (non-Claude) | Skills and config for OpenCode, Codex, and future agents |

Skills are authored in =skills.org= with one of three emission modes:

| Mode | Tangle target | Scope | Deploy |
|------|--------------|-------|--------|
| Stow-global | =all/.claude/skills/X/SKILL.md= + =all/.agents/skills/X/SKILL.md= | All sessions on all machines | =loom stow:*= → =~/.claude/skills/= |
| DotCortex-scoped | =.claude/skills/X/SKILL.md= + =.agents/skills/X/SKILL.md= | Only when CWD is DotCortex | No stow needed — loaded by CWD |
| Direct-global | =~/.claude/skills/X/SKILL.md= (absolute) | All sessions, no stow cycle | Write directly |

Current DotCortex-scoped skills: =dotcortex-*= (loom, bootstrap, gotchas, multihost, package-manifests, packages), =helmcortex-nexus=.
All other skills in =skills.org= are stow-global.

HelmCortex and its workspaces (FORGE, bridge) maintain their own skill harnesses compiled by =helmcortex-compile= from =FORGE/harness/{workspace}/SKILLS.md=. These may intentionally override global skills with project-specific content. Never duplicate a purely generic skill in a project harness — if it has no project-specific content, rely on the global version.

## Research Protocol

Before investigating unknown tool APIs, agent conventions, external system behavior,
or any problem where you would otherwise spend more than 3 tool calls speculating --
surface a Perplexity prompt for Mètsàtron to run, then stop and wait.

**Format -- output this verbatim, then stop:**

```
PERPLEXITY RESEARCH PROMPT:
[single-focus question -- include tool names, version numbers, and exactly what you need to determine]
```

Do not continue speculating while waiting. Do not attempt to answer the question yourself.
This applies to: architecture decisions, model capability questions, library version
edge-cases, and any situation where a 30-second web search collapses a multi-step rabbit hole.

This also applies when genuinely unsure of the best approach and synthesising from
the internet would improve the solution quality. Planning in Perplexity before
executing here is cheaper than burning tokens in circles.

## Model Guidance

- Main session model cannot be changed autonomously -- use `/model sonnet|haiku` yourself.
- **Opus is currently not viable.** Use `claude-sonnet-4-6` with thinking `high` or `max`
  for architecture, debugging, and novel problems.
- Subagents (via the Agent tool):
  - **Haiku (`claude-haiku-4-5-20251001`)** -- mechanical execution: file ops, grep,
    glob, reading files, git log/status, quick lookups. Zero ambiguity only.
  - **Sonnet (`claude-sonnet-4-6`)** -- standard coding, debugging, most tasks.
  - **Sonnet + thinking high/max** -- architecture, deep multi-file analysis, complex
    refactors. Never default all subagents to this tier.
- When spawning subagents via the Agent tool, always set the `model` parameter
  explicitly. Never let it default to the current session model for all subagents.
- Never silently switch model -- state which model and why, one line.
- Model hints per skill are in each skill's `model:` frontmatter field in `.claude/skills/`.
  Respect them when spawning subagents for skill-scoped work.

## Build & Apply

```bash
cd ~/DotCortex

# Tangle all org files into overlay directories
make tangle

# Tangle a single org file (faster, preferred for focused changes)
tangle-one agents.org

# Preview what stow would do (dry-run)
make preview-stow

# Stow with loom (normal workflow, requires Guix)
loom stow:x230     # X230: all linux debian x230
loom stow:t480s    # T480s: all linux debian devuan t480s
loom stow:devuan   # shared: all linux devuan

# Without loom (bootstrap, or systems without Guix)
STOW_PKGS='all linux debian devuan t480s' make safe-stow

# Package management
loom guix:apply         # apply Guix manifest
loom flatpak:apply      # apply Flatpak manifest
loom pip:apply          # install pip manifest
loom npm:apply          # install npm manifest
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
2. Add a manifest SSV block: `:tangle all/.newpkg/manifest/packages.ssv`
3. Add capture/diff/apply/health scripts: `:tangle all/.local/bin/newpkg-*`
4. Add a `.mk` Makefile fragment: `:tangle all/.mk/newpkg.mk`
5. Add `include $(HOME)/DotCortex/all/.mk/newpkg.mk` to the Makefile block in `loom.org`
6. Add loom task verbs to the Scheme control plane in `loom.org`
7. `make tangle` to generate everything

## Key Files

- `Makefile` -- build entry point -- **tangled from `loom.org`**, never edit directly
- `loom.org` -- control plane, Makefile template, batch helpers
- `agents.org` -- source of truth for `AGENTS.md`, `CLAUDE.md`, and global `~/.claude/CLAUDE.md`
- `skills.org` -- all agent skills (universal and harness-exclusive)
- `hooks.org` -- Claude settings, hooks, OpenCode config, plugin manifests
- `shell.org` -- bash/zsh rc, exports, aliases, functions, `.zshenv` (SSH PATH)
- `style.org` -- LainCore theme (fonts, colours, GTK, terminal, Emacs)
- `INSTALL.sh` -- bootstrap script for fresh machines
- `README.org` -- full Org documentation (the original grimoire)

## Finding What Owns a Config

```bash
grep -rn "tangle.*path/to/config" *.org
```

## Loom (Control Plane)

Loom is a Guile Scheme CLI (`~/.local/bin/loom`) that wraps make targets and adds batch operations. **Loom requires Guix** -- it uses Guix's guile interpreter. Without Guix, use `make` targets directly:

```bash
# With loom (requires Guix guile)
loom pip:apply
loom flatpak:diff

# Without loom (make targets work anywhere)
make pip-apply
make npm-apply
make safe-stow
```

## Bootstrap (Fresh Machine)

```bash
git clone --recursive https://gitlab.com/metsatron/dotfiles.git ~/DotCortex
cd ~/DotCortex && bash INSTALL.sh
```

See `INSTALL.sh` for the full phase-by-phase bootstrap process.

### First Tangle Needs Stubs

The Makefile includes `.mk` fragment files that don't exist until after the first tangle. Create empty stubs:

```bash
mkdir -p all/.mk
for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip; do
  [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
done
make tangle
```

### Loom Bootstrap (Chicken-and-Egg)

`loom` needs `~/.config/maak/maak.scm` (placed by stow) and Guix guile. You **cannot** use `loom stow:x230` for the first stow -- use `make safe-stow` directly. `INSTALL.sh` handles this by pre-placing `maak.scm` before stow runs.

### Guix Emacs Not in SSH PATH

On Guix machines, emacs lives at `~/.guix-extra-profiles/core/core/bin/emacs`. NOT in the default SSH PATH. `.zshenv` sources Guix profiles for all zsh invocations. For bash over SSH:

```bash
export PATH="$HOME/.guix-extra-profiles/core/core/bin:$PATH"
```

### Guix on Non-systemd Systems (Devuan, sysv-init)

1. Install `daemonize` first: `sudo apt-get install -y daemonize`
2. Use the manual install method in `INSTALL.sh` (the official `guix-install.sh` requires interactive stdin)
3. Use `ftp.gnu.org` directly -- the `ftpmirror.gnu.org` redirector sometimes has broken SSL

## Known Gotchas

### Stow Conflicts

`safe-stow` handles three conflict message formats across stow versions. It filters HelmCortex (user-managed symlink), backs up real files, removes them, then stows. On failure, auto-retries with `--ignore=HelmCortex`.

After repo rename (`.dotfiles` -> `DotCortex`), remove dangling symlinks first:

```bash
find ~ -maxdepth 5 -lname "*/.dotfiles/*" -not -path "*/.git/*" -delete
```

### /tmp Permissions Break Tangle and Guix Pull

If `/tmp` has restrictive permissions (`755` instead of `1777`), both fail:

- Tangle: emacs `org-persist` can't create temp directories
- Guix pull/build: sandbox can't bind-mount

Fix: `sudo chmod 1777 /tmp`. Tangle-only workaround: `TMPDIR=~/.cache/tmp make tangle`

### pipefail + grep -v

Under `set -euo pipefail`, `grep -v PATTERN` exits 1 when all lines are filtered. Wrap: `{ grep -v PATTERN || true; }`

### LD_PRELOAD Warning

Systems with `libgtk3-nocsd` in `LD_PRELOAD` emit a harmless warning on Guix commands. Ignore it or `unset LD_PRELOAD`.

### Guix Substituter Display Bug

`guix package` occasionally crashes with `Wrong type argument in position 1: #f` during substitute progress display. Cosmetic only -- retry the command.

### Absolute Symlinks in Overlay Dirs Abort Stow

If an org file tangles an absolute symlink (e.g. `.config/guix/current`), stow refuses to manage it. Remove it from the overlay dir -- they're machine-specific. `INSTALL.sh` auto-cleans these.

### Flatpak Audio Dead After PulseAudio Restart (T480s)

Killing PulseAudio (`pulseaudio -k`) destroys `/run/flatpak/pulse/` which `flatpak-session-helper`
created at login. The helper does not recreate it automatically when PA restarts. Flatpak apps
(FireDragon, etc.) have `PULSE_SERVER=unix:/run/flatpak/pulse/native` baked into their sandbox
env, but the socket is gone. Menu restart reuses the existing sandbox with a stale dead tmpfs
bind-mount -- it does not help.

Fix:


```bash
# 1. Recreate the socket directory
sudo mkdir -p /run/flatpak/pulse
sudo chown $USER:$USER /run/flatpak /run/flatpak/pulse
ln -s /run/user/1000/pulse/native /run/flatpak/pulse/native
touch /run/flatpak/pulse/config

# 2. Verify it's connectable
PULSE_SERVER=unix:/run/flatpak/pulse/native pactl info

# 3. Full kill + relaunch the Flatpak app (NOT menu restart)
pkill firedragon   # or whichever app
# then reopen from launcher
```

### XFCE Screenshot Region Tool Leaves Ghost InputOnly Window (T480s)

Taking a screenshot with the region-select tool (xfce4-screenshooter or similar) creates a
fullscreen `InputOnly` + `Override Redirect` X window for the selection overlay. If the tool
crashes or is killed mid-selection, this ghost window is left mapped over the entire screen.
It is completely invisible but swallows all mouse clicks and keyboard input. Symptoms: cursor
only appears briefly during Alt+Tab, can't click or type anywhere in the desktop.

Diagnosis and fix (run from a TTY or any terminal with DISPLAY access):

```bash
export DISPLAY=:0 XAUTHORITY=~/.Xauthority

# Find the ghost window — look for InputOnly + Override Redirect + 1920x1080+0+0
xwininfo -root -children | grep "1920x1080+0+0"
# Note the window ID (e.g. 0x5000004), then confirm:
xwininfo -id 0x5000004 | grep -E "Class|Override|Map State"
# Should show: Class: InputOnly, Override Redirect State: yes, Map State: IsViewable

# Kill it
xdotool windowkill 0x5000004

# Also reset the root cursor in case it was hidden
xsetroot -cursor_name left_ptr
```

### Xephyr Exit Leaves Ghost InputOnly Window Without =-no-host-grab=

Xephyr launched without =-no-host-grab= grabs the host keyboard and pointer when active. If Xephyr exits abnormally (guest WM crash, SIGKILL, display error), the input grab is not released and an invisible fullscreen =InputOnly= + =Override Redirect= X window remains on the host display, swallowing all mouse clicks and keyboard input. Symptoms: can't click anything on the host desktop, cursor may disappear.

Prevention: always pass =-no-host-grab= to every Xephyr invocation. All sanctuary launch scripts in =distrobox.org= include it.

Emergency recovery (SSH in from another machine or switch to a TTY):

```bash
export DISPLAY=:0 XAUTHORITY=~/.Xauthority

# Find the ghost window — look for the fullscreen InputOnly override-redirect entry
xwininfo -root -children | grep "1920x1080+0+0"
# Note the window ID, confirm it:
xwininfo -id 0x4e00004 | grep -E "Class|Override|Map State"
# Should show: InputOnly, Override Redirect State: yes, IsViewable

xdotool windowkill 0x4e00004
xsetroot -cursor_name left_ptr   # restore cursor if hidden
```

### xfconf Symlink Means xfconfd Writes Directly to DotCortex

The sanctuary-sx launch script symlinks the guest home's =xfce-perchannel-xml= directory to =linux/.config/sanctuary-sx/xfconf/= in the DotCortex tree. This means xfconfd writes new channel XML files directly into the repo whenever an XFCE app first accesses xfconf. Any new app installed in the sanctuary will silently create a channel file in DotCortex source.

Before every =git add= involving xfconf: run =git status linux/.config/sanctuary-sx/xfconf/= and review new files. If a new channel is ephemeral or machine-specific, add it to =linux/.config/sanctuary-sx/xfconf/.gitignore= *before* staging anything. Never run =git add -A= or broad-pathspec adds that sweep up new xfconf channel files without review.

### Host X Utilities Not in Guix Container PATH

Tools from the host Debian system (=setxkbmap=, =xrandr=, =xdpyinfo=, etc.) are not in the PATH inside a Guix-backed Distrobox sanctuary. The Guix container's =/usr/bin= belongs to the container image; the host filesystem is mounted read-only at =/run/host/=. Any =.desktop= file, shell script, or XDG autostart entry that needs host X utilities must use the full path:

```
/run/host/usr/bin/setxkbmap -layout us -variant colemak
/run/host/usr/bin/xrandr --query
```

Bare command names fail silently in XDG autostart context (the session manager does not propagate the error) and visibly in shell scripts (command not found).

### XFCE 4.20 xfsettingsd Silently Drops XkbVariant

xfsettingsd in the XFCE 4.20 Guix build applies =XkbLayout= from =keyboard-layout.xml= but silently discards =XkbVariant= on session startup, reverting to the base layout (e.g., QWERTY for =us=) even when the channel file has the correct variant. The setting appears correct in the XFCE Keyboard GUI but does not take effect.

Fix: add an XDG autostart =.desktop= entry that runs =setxkbmap= explicitly after session initialization. The autostart entry runs after xfsettingsd, so it wins. In Guix containers, use the full host path:

#+BEGIN_SRC conf
[Desktop Entry]
Type=Application
Name=Colemak keyboard layout
Exec=/run/host/usr/bin/setxkbmap -layout us -variant colemak -option terminate:ctrl_alt_bksp
NoDisplay=true

## Non-Claude Agent Rules

These rules apply to OpenCode, Codex, and any other non-Claude harness:

1. **Edit harness config through canonical source** -- `.claude/`, `.opencode/`, `.codex/`, and `.agents/` outputs may all be managed here, but changes must be made in the owning `.org` source and re-tangled. Do not hand-edit emitted harness files unless the user explicitly asks for that exact path.
2. **Agent config goes in the right directory** -- `.opencode/` for OpenCode-specific config, `.codex/` for Codex-specific config, `.claude/` for Claude-specific config, and `.agents/` for universal non-Claude skills. Shared doctrine may intentionally emit to multiple harness directories from one `.org` source.
3. **Skills are authored in `skills.org`** -- tangle to `all/.agents/skills/X/SKILL.md` for stow-global skills, `.agents/skills/X/SKILL.md` for DotCortex-scoped skills, or `.opencode/skills/X/SKILL.md` for OpenCode-exclusive skills. Do not write skill files directly.
