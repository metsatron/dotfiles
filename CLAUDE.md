# DotCortex — Literate Dotfiles System

## What This Is

DotCortex is Metsatron's declarative, literate, reproducible dotfiles system. Org-mode files are the single source of truth. They tangle into overlay directories which GNU Stow symlinks into `$HOME`.

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
4. **Stow via loom** — use `loom stow:x230` or `loom stow:t480s`, not `make safe-stow`. The `make safe-stow` target is only for first-time bootstrap before loom is functional.
5. **Follow existing patterns** — new package managers get: `.org` file + SSV manifest + capture/diff/apply/health scripts + `.mk` Makefile fragment + loom verbs in `loom.org`.
6. **Never suggest next steps after editing org files** — do not tell the user to tangle or stow. The user knows the workflow (`tangle-one <file>.org`, `loom all`, `loom stow:*`). Never suggest `make tangle`.
7. **Never apply quick fixes or workarounds** — always fix the root cause in the `.org` source. Quick fixes (env overrides, symlink hacks, one-off patches) accumulate into broken state. If INSTALL.sh solves a problem, reproduce that solution in the relevant `.org` file so loom verbs are self-contained and reproducible.
8. **INSTALL.sh is the reproducibility reference** — when something fails on a fresh system, check INSTALL.sh first. It documents every bootstrap step and lesson learned. Loom verbs and apply scripts must be self-sufficient: they should handle their own bootstrapping (like pip-apply bootstrapping broken Guix pip) rather than assuming INSTALL.sh has already run.
9. **Never mount, move, or delete user data without explicit confirmation** — always show the exact command and wait for approval. Never assume mount points are free. `~/mnt/x230` is an SSHFS mount to the live X230 machine.
10. **Always use stable device paths for block devices** — never use `/dev/sdX` names in LUKS, fstab, crypttab, or mount commands. Use `/dev/disk/by-uuid/`, `/dev/disk/by-id/`, or `/dev/disk/by-partuuid/` instead. SCSI device names change when drives are re-enumerated (e.g. a USB drive probe reorders `sd*` letters), which breaks LUKS mappings and mount entries.
11. **When asked to do something, DO it** — do not just show the command and wait. If the user says "copy X to Y", run the command. Only ask for confirmation on destructive or irreversible operations (deleting data, force-pushing, dropping tables). Copying, syncing, and building are not destructive.
12. **Always consider whether operations need sudo/root** — system disks, root-owned files, and protected paths require sudo. Include it from the start, don't wait to be corrected.
13. **Never output generic emotional-support boilerplate** — no "I hear your frustration", no "I understand", no "I'm here when you're ready". If you messed up, say what you did wrong concretely and fix it. If there's nothing to do, say nothing.

## Behavioural Constraints

- For mechanical tasks (file ops, tangling, stowing, grepping): act first, report what changed. No preamble.
- For ambiguous or architectural tasks: think out loud, ask the ONE most important question if genuinely unclear, then proceed.
- DO NOT add disclaimers, warnings, or "note:" hedges unless there is a genuine blocking issue.
- DO NOT summarise what you just did — the output speaks for itself.
- DO NOT produce a wall of options when a clear best path exists. Pick it and say why in one sentence.
- Use extended thinking silently for non-trivial tasks before acting. Do not narrate the thinking process.
- After solving a non-trivial problem, consider whether it warrants a `/reflect` or a new skill — flag it, don't silently proceed.
- MEMORY.md can be updated autonomously. CLAUDE.md changes require explicit user approval.
- Before using any tool for the first time in a session, load the relevant skill if one exists.

## Tool Verification

- NEVER claim a tool, command, or file does not exist based on an error message alone. A warning or partial failure is not absence. Always verify: run `<tool> --help`, `which <tool>`, or `ls <path>` before concluding something is unavailable.
- NEVER invent command syntax. If you don't know a tool's API, run `--help` first and read the actual output before constructing any command. Fabricated flags are worse than doing nothing.
- When a command emits warnings before working output, strip the warnings with `2>/dev/null` and evaluate the actual output.
- If a tool behaves unexpectedly, the debugging sequence is: (1) `--help` or `man` — read the actual API, (2) run the simplest possible invocation, (3) report what you found, not what you assumed.

## Model Guidance

The main session model cannot be changed autonomously — use `/model <opus|sonnet|haiku>` yourself.

For subagents:
- Mechanical execution (file ops, grep, format, known commands): spawn with model: haiku
- Standard coding with clear spec: spawn with model: sonnet
- Architecture, debugging, novel problems: keep in main Opus context

When a task is purely mechanical and self-contained, suggest spawning it as a subagent rather than doing it inline, so it runs in isolated context with a cheaper model and doesn't pollute the main thread.

## Common Workflows

```bash
loom all && loom stow:x230      # full rebuild (X230)
loom all && loom stow:t480s     # full rebuild (T480s)
tangle-one term.org             # tangle a single file
loom                            # list all verbs
# Bootstrap (no loom yet): make tangle && STOW_PKGS='all linux debian devuan t480s' make safe-stow
```

## Key Files

- `Makefile` — tangled from `loom.org`, never edit directly
- `loom.org` — control plane, Makefile template, batch helpers
- `shell.org` — bash/zsh rc, exports, aliases, functions, prompt, `.zshenv` (SSH PATH)
- `style.org` — LainCore theme (fonts, colours, GTK, terminal, Emacs)
- `INSTALL.sh` — bootstrap script for fresh machines
- `README.org` — full Org documentation (the original grimoire)
- `.claude/MEMORY.md` — session facts + user model persisted by `/reflect` (auto-updated, max 2000 chars)

## When Working on DotCortex

- Always edit `.org` source, never tangled output
- The Makefile is tangled from `loom.org` — edit `loom.org`, not Makefile
- Test with `make tangle` before stowing
- Use `make preview-stow` to dry-run before applying
- After adding new package manager support, add loom verbs AND make targets
- When searching for a tool, check Guix profiles (`~/.guix-extra-profiles/core/core/bin/`) before assuming it's not installed

## Skills (load on demand)

- **dotcortex-gotchas** — stow conflicts, tangle failures, Guix installer issues, /tmp permissions, pipefail
- **dotcortex-packages** — package manifest table, SSV format, adding new package managers
- **dotcortex-multihost** — multi-machine deployment, overlay scoping, HelmCortex integration, bootstrap
- **context-hygiene** — context window management, when to compact/delegate
- **obsidian-cli** — official Obsidian CLI for vault ops, note CRUD, search, tasks, properties, plugin debugging
- **obsidian-markdown** — Obsidian-flavored markdown: wikilinks, embeds, callouts, properties, tags
- **obsidian-bases** — Obsidian Bases `.base` files: filters, formulas, views, summaries
- **json-canvas** — JSON Canvas `.canvas` files: nodes, edges, groups
- **defuddle** — clean markdown extraction from web pages via Defuddle CLI
- **gh** — GitHub CLI for repo ops, PRs, issues, NEXUS repo updates
- **nexus-index** — index of curated skill/agent repos in NEXUS/git

## Skills Ecosystem

- The `skills` npm package is managed via npm.org manifest — install/update with `loom npm:apply`
- Add skills: `npx skills add <owner/repo> --agent claude-code`
- Update installed skills: `npx skills update`
- Discover skills: `npx skills find [query]`
- NEXUS source repos: `/home/metsatron/mnt/x230/HelmCortex/NEXUS/git/`
- Update NEXUS repos: `/nexus-update`
