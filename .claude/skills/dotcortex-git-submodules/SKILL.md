---
name: dotcortex-git-submodules
description: Create, register, and update DotCortex git submodules — push-to-create over SSH (no glab/token; the SSH key IS the capability), the commit-inside-then-bump-pointer order, submodules.org registration, the dotcortex-guard multi-writer override, keeping source art out of stowed theme dirs, and master-not-main on new repos. Load before creating a submodule repo or committing changes inside one.
---

# DotCortex Git Submodules

Icon themes, GTK/xfwm themes, editor packs, and many other payloads in DotCortex are **separate git repositories** mounted as submodules — mostly Mètsàtron's own `git@gitlab.com:metsatron/*` repos (~302 of them). The parent repo tracks only each submodule's commit pointer; the files live in the child repo. Canonical branch is **master** in both the parent and every submodule — there is no `main`.

## Creating a NEW submodule repo yourself — push-to-create over SSH

**You do not need `glab`, a token, or the GitLab API.** DotCortex already pushes over SSH, and GitLab's *push-to-create* makes a new **private** project automatically on first push to a path that does not exist yet, using that same SSH key. Absence of a CLI is not absence of the capability — the capability is the SSH key. `which glab` failing is not "I cannot create a repo"; check `ssh -T git@gitlab.com` → `Welcome to GitLab, @metsatron!` and proceed.

1. Confirm the key: `ssh -T git@gitlab.com` (with `-o BatchMode=yes`) → `Welcome to GitLab, @metsatron!`.
2. Confirm the repo does NOT already exist: `git ls-remote git@gitlab.com:metsatron/<name>.git` — **real exit 128 + "project could not be found" = safe to create**. Check the *real* exit, not a piped one — a pipe (`… | head`) masks `ls-remote`'s exit behind `head`'s 0.
3. Build the content locally, on master: `git init -b master` — `git init` may default to `main`, which is an EXTREME WARMAPCODEX violation baked permanently into a new repo, so pass `-b master` and verify `git branch --show-current` before pushing. Commit.
4. `git remote add origin git@gitlab.com:metsatron/<name>.git`
5. `GIT_SSH_COMMAND='/usr/bin/ssh -o BatchMode=yes -o PreferredAuthentications=publickey' git push -u origin master` → GitLab replies **"The private project metsatron/<name> was successfully created."**
6. **Verify visibility in the web UI** (`https://gitlab.com/metsatron/<name>`). You cannot query it over SSH without a token, and getting it wrong publishes whatever the repo holds — for license-restricted payloads, have Mètsàtron eyeball it.

## Registering it in DotCortex

- `git submodule add git@gitlab.com:metsatron/<name>.git <path>` (clones it in, writes `.gitmodules`).
- **Add the path to `submodules.org`** (the inventory) *before* bumping the parent pointer — its policy: "Parent gitlink bumps may be committed only when the path is listed here." (The ~50 `linux/.local/share/icons/*` submodules predate that inventory and are not listed — a known gap; do not assume the inventory is complete.)
- Commit `.gitmodules` + the gitlink path + `submodules.org` together.

## Editing files inside an existing submodule — commit-inside-then-bump order

`git add <file-inside-a-submodule>` from the DotCortex root **fails** with *"Pathspec is in submodule"*, and committing in the parent without committing in the child leaves your new files **silently absent** from the tracked pointer. Order:
1. `git -C <submodule-path> add … && git -C <submodule-path> commit -m …` — commit INSIDE the child first.
2. `git -C <submodule-path> push` — push the child.
3. `git -C ~/DotCortex add <submodule-path>` — bump the parent gitlink pointer, then commit the parent.

## Committing in a multi-writer tree

DotCortex has a `dotcortex-guard` pre-commit hook that **refuses commits from a dirty tracked worktree**. When another lane (e.g. a peer agent's session) has staged work you must not touch, commit surgically: `DOTCORTEX_GUARD_ALLOW_DIRTY=1 git commit -F - -- <exact paths>`. The pathspec (`--only` mode) commits just your paths and leaves the other lane's staged entries intact. Never `git add -A`.

## Deploying to the live tree

Payloads live at `linux/.local/share/icons/<Name>` (or `linux/.themes/<Name>`) and reach `~/.local/share/icons/` via `loom stow:<machine>` (or `icons-home-sync`). Keep **source material / build inputs OUT of a stowed XDG theme dir** — icon-cache scanners walk theme trees and choke on non-theme files (slow cache rebuilds, spurious "corrupt file" reports). Provenance and rebuild recipes belong in a `PROVENANCE` file, not 20 MB of raw `.icns`/`.tiff`/`.xpm` sitting in the scanned dir.
