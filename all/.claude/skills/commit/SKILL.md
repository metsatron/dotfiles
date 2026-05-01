---
name: commit
description: /commit — Structured Git Commit
model: claude-sonnet-4-6
---

# /commit — Structured Git Commit

You are creating a well-structured git commit. The user may provide a hint: $ARGUMENTS

## Steps

1. Run `git status` (never `-uall`) and `git diff --staged` + `git diff` to understand all changes.

2. **Classify the change type:**
   - `feat` — new feature or capability
   - `fix` — bug fix
   - `refactor` — restructuring without behavior change
   - `docs` — documentation only
   - `chore` — maintenance, config, dependencies
   - `tangle` — org source block changes that affect tangled output

3. **Determine scope from file paths:**
   - `emacs` — emacs.org, Spacemacs config
   - `shell` — shell.org, bash/zsh config
   - `flatpak` — flatpak.org, Flatpak management
   - `loom` — loom.org, Makefile, control plane
   - `style` — style.org, LainCore theme
   - `tools` — tools.org, misc tooling
   - `stow` — overlay dirs, stow config
   - `pkg` — package manifests (pip, npm, cargo, guix, etc.)
   - Use the most specific scope that fits

4. **Build the commit message:**
   ```
   TYPE(SCOPE): one-line summary (imperative mood, <72 chars)

   - bullet point details of what changed
   - focus on WHY not just WHAT

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   ```

5. **Refresh visibility before staging:**
   - If the work changes outstanding tasks, update the relevant `~/HelmCortex/LOGS/TODO/{workspace}.md` file.
   - If the work is machine-specific, update `~/HelmCortex/LOGS/TODO/Machines/{hostname}.md`.
   - If a durable lesson crystallized, run or recommend `/reflect` and persist the lesson to the narrowest real source of truth before committing.
   - If no TODO or reflection update is warranted, say so briefly in the commit report.

6. **Stage specific files** — NEVER use `git add .` or `git add -A`. Add files by name. If unsure which files belong, ask.

7. **Commit** using a HEREDOC for the message to preserve formatting.

8. Show `git log -1` to confirm.

9. **Push and sync — do this, don't describe it:**
   - Run `git push` immediately after every DotCortex commit. Do not wait to be asked.
   - For each other machine with a separate DotCortex checkout (X230, T480s):
     a. **Check state first** — SSH in and run `git status --short`, `git diff --name-only`, and `git diff --cached --name-only`.
     b. **If the remote has only untracked dirt** — report it, but it does not block sync. Pull and stow normally.
     c. **If the remote has tracked dirt** — compare the exact changed files against the incoming upstream slice before touching history. Do not assume every dirty remote needs an immediate WIP commit.
     d. **Only preserve-and-merge when there is no real overlap** — if the dirty tracked files are byte-identical to `origin/master` or to the incoming local slice, commit them on the remote as a preservation/WIP checkpoint, then merge `origin/master`, then stow. This is safe because the tracked dirt is only local state, not conflicting content.
        ```bash
        ssh x230 'cd ~/DotCortex && git status --short && git diff --name-only && git diff --cached --name-only'
        ssh x230 'cd ~/DotCortex && git add <exact-files> && git commit -m "wip(x230): preserve local state before merge"'
        ssh x230 'cd ~/DotCortex && git merge --no-edit origin/master && loom stow:x230'
        ```
     e. **Stop on real overlap** — if the remote tracked files differ from the incoming upstream content, stop and report the overlapping paths. Do not auto-commit, auto-merge, or resolve conflicts autonomously.
     f. **Clean remote fast path** — if the remote tracked worktree is clean, use the normal path:
        ```bash
        ssh x230 'cd ~/DotCortex && git pull --ff-only && loom stow:x230'
        ```
   - If a machine is NFS-mounted (same working tree, no separate checkout), skip the pull but check state and re-run stow.
   - Report what was done, not what to do.

## Rules

- If there are no changes, say so and stop.
- Refuse to commit from a dirty tracked worktree. If tracked unstaged changes exist outside the intended commit, stop and ask the user whether to split, stage, or stash them first.
- If changes span multiple unrelated scopes, suggest splitting into multiple commits.
- If the user's hint conflicts with what the diff shows, trust the diff.
- Never commit generated/tangled output without the canonical `.org` source in the same commit.
- Never use `git add .`, `git add -A`, or a broad pathspec that sweeps unrelated files into the commit.
- Cross-machine sync is always explicit: `git pull --ff-only` before editing on any machine. Uncommitted work on one machine is not synchronisation.
- Never push directly to a remote working tree over SSH (`git push ssh://...`) — always push to origin and pull on the remote.
- When a remote checkout is dirty, compare exact files before merging; untracked-only dirt is usually harmless, tracked overlap is the actual blocker.
- Remember: `.org` files are the source of truth, tangled output files are generated.
- Commit closeout is a visibility gate: TODO state and reflection-worthy lessons should not be left only in chat context.
