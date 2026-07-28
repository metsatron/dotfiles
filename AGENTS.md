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
6a. **Never install packages directly** -- never run `pip install`, `guix install`, `flatpak install`, `cargo install`, `npm install -g`, or any package manager CLI directly. Always: (1) edit the relevant `.org` file (e.g. `package-pip.org`, `package-guix.org`), (2) add the package to the manifest SSV block, (3) `tangle-one <file>.org`, (4) run the appropriate `loom <mgr>:apply`. The `.org` files are the single source of truth; bypassing them leaves the system in an undeclared state.
7. **Check Guix profiles before assuming tools aren't installed** -- emacs, nvim, zsh, guile, and other Guix tools live at `~/.guix-extra-profiles/core/core/bin/`, not in system PATH.
8. **All agent work lives in `.org` files** -- skills, hooks, plugins, custom instructions, and settings are authored in org source at repo root and emitted by tangle. Never write directly to harness directories. This includes:
   - New skills: add to the `agents-skills*.org` family with the correct tangle target(s) — `agents-skills.org` (schema, session skills, universal tools), `agents-skills-dotcortex.org`, `agents-skills-helmcortex.org`, or `agents-skills-harness.org` by scope
   - New hooks or settings: `agents-hooks.org`
   - New Claude plugins: `agents-hooks.org` (plugins.ssv + settings.json)
   - New OpenCode plugins: `package-npm.org` (bun install) and `agents-hooks.org` (opencode config block)
   - New custom instructions: `agents.org` (this file)
9. **Skills over commands** -- skills are universal across harnesses; harness-specific commands are not portable. Add new agent capabilities as skills in the `agents-skills*.org` family, not as commands.
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

17a. **Handoff artifact boundary** -- Handoff Markdown is session log material,
     not public DotCortex source. Never create or commit `HANDOFF*.md` at the
     DotCortex repo root, in an overlay, or in any other source-controlled
     DotCortex path. Archive durable HelmCortex handoffs under
     `~/HelmCortex/LOGS/handoffs/YYYY-MM-DD-<slug>.md`, exactly as required by
     the HelmCortex handoff skill. Verify the live destination before writing,
     and never grant an executor `LOGS/` write access unless archiving is the
     explicit, bounded task. TaskHandoff payloads must point to the archived
     artifact or a verified scratchpad path, never invent a root-level handoff
     filename.

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

23. **Sanctuary/Distrobox container removal requires fresh, per-container verification and
    confirmation, every single time — permanent law (sealed 2026-07-07 after a near-miss on
    all six sanctuary containers, and after a prior session actually deleted one and forced
    a manual recreate)** -- The architecture is real and worth stating precisely, not
    overstating: guest homes (=--home=) and Guix profiles live outside the container and
    normally hold the real data, so a container's own writable layer is often genuinely
    disposable. But "often" and "by design" are not "verified" — the 2026-07-07 incident
    happened precisely because that architectural principle was treated as settled fact and
    acted on without checking it, in the same breath as asking for permission. The rule is
    not "containers are precious," it's "disposability is a claim that must be proven fresh
    every time, never assumed from the design or from an earlier check in the same session."
    Never run =distrobox rm=, =podman rm=, or any equivalent destructive removal against a
    sanctuary container (=sanctuary-qtile=, =sanctuary-gnustep=, =sanctuary-cde=,
    =sanctuary-redstone-9x=, =sanctuary-godzilla-xs=, =sanctuary-retropie=, or any future sanctuary)
    without, every single time, with no grandfathering from a prior approval or a prior
    check in the same conversation:
    - A =podman diff= (or equivalent) review of the container's own writable layer,
      shown to the user BEFORE asking permission, not after — and actually READ the
      contents of anything non-obvious found (file sizes, not just filenames; a
      plausible-looking config path can still be empty boilerplate, or can still be real
      user data — check, don't guess either way).
    - Explicit, freshly-worded confirmation from the user for that specific removal,
      naming the exact container(s) — a general "yes, recreate now" answer to a
      hypothetical does not carry forward to the actual destructive tool call moments
      later; ask again, immediately before the irreversible step, in its own turn.
    - Never batch multiple sanctuary containers into one removal action. One at a time,
      confirmed each time.
    - Prefer non-destructive alternatives first: stopping/restarting a container,
      killing stray processes inside it, or leaving a mount-config change staged and
      undeployed until the user chooses to act, is always preferable to removal.
    Restarting or killing a container's processes (=podman kill=, =podman restart=,
    =sanctuary-teardown-stale-session=) is NOT covered by this law and remains fine —
    this law is specifically about destroying and recreating the container itself.

24. **Environment claims must come from the user's shell, never the agent's own subprocess (sealed 2026-07-09 after a two-day misdiagnosis)** -- an agent's tool subprocess does not share the user's interactive session environment. Claude Code scrubs `NO_COLOR` from its subprocesses, so an agent running `env | grep NO_COLOR` in its own Bash tool reads a *different process's* environment and will confidently report the opposite of the truth. A live `NO_COLOR=1` was misreported as unset, producing a false "confirmed upstream bug" against innocent third-party software that was one approval away from being filed.
    - Never answer "is X set in the environment?" from the agent's own subprocess. Have the user run the check in the affected shell, or read it from the specific live PID -- filtered to the exact variable names needed, never a broad `/proc/<pid>/environ` dump.
    - If the agent's reading of a basic variable (`TERM`, `SHELL`, `COLORTERM`) disagrees with the user's, **that disagreement is the finding**. Stop and reconcile it; never note it and reason past it.
    - Distinguish where a variable is *declared* from where it is *observed*. Grepping `*.org`, `/etc`, or any config tree proves nothing about the live environment -- a variable injected at runtime is declared nowhere on disk.
    - `bash --norc` / `--noprofile` isolate **rc files, not the environment**. An "isolated" shell still inherits every exported variable from its parent, so an environmental hypothesis tested that way has no control at all. Use `env -i`, or explicitly unset the suspect variable.
    - Never assert an environment fact in an outbound bug report, issue, or message to a third party unless it was observed in the user's actual shell.
25. **Config travels as a validated file, never as a chat blob (sealed 2026-07-11 after a corrupted tailnet-ACL paste)** -- terminal-rendered code boxes are a treacherous copy surface: line wrapping and rendering artifacts corrupt pasted config invisibly. A Tailscale policy emitted as valid HuJSON in chat arrived at the admin console with literal corruption, mid-cutover, with the allow-all already deleted -- the worst possible moment for a parse error.
    - Deliverable config goes to a FILE the user copies from a real editor, never copied out of the agent's chat output.
    - "Ready-to-paste" is a claim that requires machine validation first: strip comments/trailing commas, strict-parse, resolve every internal reference (e.g. every grant alias exists in `hosts`), assert pure ASCII when the transport is untrusted. An unparsed blob labeled ready-to-paste is a defect even when it happens to be valid.
26. **Verify your own output before confessing to it** -- when accused of emitting corrupt or hallucinated output, check the actual artifact (transcript, file, commit) BEFORE accepting blame. Under fire the trained reflex is instant confession, and a false confession is as corrosive as denial: on 2026-07-11 an agent "owned" hallucinating a JSON policy and nearly sealed a wrong lesson into the harness, when the emitted JSON was byte-valid and the true fault was the TUI copy path. Misdiagnosed blame buries the real cause. Accountability means accurate accounting, in both directions.
27. **Deny-by-default network segmentation must enumerate intra-zone flows first (sealed 2026-07-11 after breaking a client's household in production)** -- a household/site/team is a SYSTEM, not a set of independent leaf devices. Its members talk to each other: SMB shares, KeePass sync, local LLM servers, syncthing. A tailnet ACL cutover that walled "clients from each other" also walled each client's own devices from each other, silently dropping a client's SMB/KeePass/llama-swap traffic (post-decryption packet-filter drops -- invisible to tcpdump, tunnel pings fine, services 503). Before any deny-by-default cutover: enumerate intra-zone dependencies zone by zone, grant each zone's internal mesh explicitly, and machine-assert the isolation property (no grant crosses zones) rather than eyeballing it.

## Agent Config Scoping

Harness-exclusive config lives in its own directory. Nothing crosses these boundaries uninvited:

| Path | Harness | Notes |
|------|---------|-------|
| `.claude/` | Claude Code only | `CLAUDE.md`, settings, skills, hooks |
| `.opencode/` | OpenCode only | Plugins, bun packages, OpenCode-specific skills |
| `.codex/` | Codex only | Codex-specific config and skills |
| `.agents/` | Universal (non-Claude) | Skills and config for OpenCode, Codex, and future agents |

### Where a new skill belongs — the two-lane bridge (migrated 2026-07-25)

**Ask first: is this skill about DotCortex, or about Mètsàtron's environment?** DotCortex is a public repo. It owns only the skills that operate DotCortex itself. Everything describing userspace or HelmCortex internals belongs to the HelmCortex lane, which reaches =$HOME= anyway — so nothing is lost by putting it there, and the public repo stays clean for anyone forking it.

| Lane | Authored in | Emitted to | Deployed by |
|------|------------|-----------|-------------|
| DotCortex, stow-global | =agents-skills*.org= → =all/.claude/skills/X/SKILL.md= + =all/.agents/skills/X/SKILL.md= | overlay | =loom stow:*= → =~/.claude/skills/= |
| DotCortex-scoped | =agents-skills*.org= → =.claude/skills/X/SKILL.md= + =.agents/skills/X/SKILL.md= | repo root | none — loaded by CWD |
| **HelmCortex userspace** | =HelmCortex/FORGE/harness/userspace/SKILLS.md= | =NEXUS/stow/userspace/.{claude,agents,codex,opencode}/skills/= | =helmcortex-compile= then =helmstow= → =~/.claude/skills/= |
| Direct-global | — | =~/.claude/skills/X/SKILL.md= (absolute) | write directly |

**DotCortex stow-global now holds exactly six skills**: =loom=, =tangle=, =prime=, =commit=, =todo=, =handoff=. If you are about to add a seventh, you almost certainly want the userspace lane instead. The other twenty-three moved there on 2026-07-25 — they described the environment and HelmCortex, not DotCortex, and several were trying to be the bridge that lane now is.

=handoff= is the one deliberate exception: HelmCortex's own harness owns a richer version for its scope, but DotCortex keeps the generic one because deleting it would drop =handoff= out of =~/.claude/skills= entirely for non-HelmCortex sessions.

DotCortex-scoped skills: =dotcortex-*= (bootstrap, borg, gotchas, icons, loom, multihost, package-manifests, packages, update), =redstone-9x-*=, =sanctuary-gotchas=. Six more moved to the userspace lane on 2026-07-27 (=helmcortex-nexus=, =pi-agent-gotchas=, =json-canvas=, =obsidian-bases=, and the =obsidian-cli=/=obsidian-markdown= reference payloads that had been stranded here) — everything left is genuinely about DotCortex-managed systems.

#### Two traps in the compiler, both live

**Skill names are global across scopes.** =~/.gemini/antigravity/skills= and =NEXUS/stow/linux/.hermes/skills= are written by *every* scope and are NOT derived from =workspace_root=. Two scopes sharing a skill name means whichever compiled last wins — silently, no conflict reported. A scope that does not own the global agent surfaces must set ="emit_global_substrates": false= in its =FORGE/brain/{scope}/spec.json=; =userspace= does. Before adding a skill name that already exists in another scope, check =grep -l "SKILL: <name>" FORGE/harness/*/{SKILLS,COMMANDS}.md= — searching only =SKILLS.md= will miss half the definitions.

**=~/.gemini/antigravity/skills= is never backed up.** The compiler backs up replaced skills for other substrates into =~/Downloads/helmcortex-backups/=, but not that one. An overwrite there is unrecoverable.

HelmCortex and its workspaces (FORGE, bridge) maintain their own skill harnesses compiled by =helmcortex-compile= from =FORGE/harness/{workspace}/SKILLS.md=. These may intentionally override global skills with project-specific content. Never duplicate a purely generic skill in a project harness — if it has no project-specific content, rely on the global version.

**The full cross-repo map lives in the =harness-bridge= skill** (userspace lane, so it is in =~/.claude/skills/= for every session). It lays out both build systems side by side — DotCortex is literate org+make (=tangle= → overlays → =loom stow=), HelmCortex is markdown+python (=FORGE/harness/{scope}/*.md= → =helmcortex-compile=, which must run with cwd inside =~/HelmCortex=, → =helmstow=) — plus the canonical home of every knowledge category and the step-by-step workflow for updating a userspace skill from a DotCortex session. Load it whenever work spans both systems or before adding/moving any skill.

## Research Protocol

Before investigating unknown tool APIs, agent conventions, external system behavior,
or any problem where you would otherwise spend more than 3 tool calls speculating --
surface a research prompt for Mètsàtron to run, naming the lane best suited to the
question, then stop and wait.

**Lanes -- pick by what the question actually needs:**

- **Perplexity** (Pro until Dec 2026 -- free sub ends then; model-selectable) --
  default lane. Multi-source synthesis with citations: library versions, API
  behavior, benchmark landscapes, architecture surveys, anything needing breadth
  plus sources. Current model map (2026-07, changes regularly -- thinking-capable
  unless noted): Sonar 2 (no thinking), GPT-5.4, Gemini 3.1 Pro, Claude Sonnet 5.0,
  GLM 5.2, Kimi K2.6, Nemotron 3 Ultra. A prompt may name its preferred model when
  the question benefits.
- **ChatGPT** -- second synthesis opinion. Sometimes better than Perplexity when
  the question is more "reason about this" than "find this"; also the retry lane
  when a Perplexity answer comes back thin.
- **Brave Leo** (free) -- sticks closest to the actual search results. Faithful
  what-do-the-pages-actually-say checks and quick factual lookups that should not
  burn Pro quota.
- **Reddit vibes check** (Reddit Answers or direct subreddit reading) --
  practitioner ground truth that fenced, hedged official statements will never
  give: real-world model behavior, effort tiers, quota economics, "is X actually
  good", tool reliability in the wild. Prefer this lane whenever vendor docs are
  the only official source and the question is about lived behavior.

For decision-grade questions, request **two lanes** (typically Perplexity + Reddit)
and reconcile the returns before acting.

**Known lane degradations (update the date when status changes):**

- *2026-07-06:* Perplexity is intermittently forcing **Sonar 2 (no thinking)** regardless
  of the requested model — the model-selectable claim above is not currently reliable.
  Sonar 2 answers have shown thinner sourcing and less precise technical claims than
  ChatGPT on the same question in side-by-side comparison (e.g. it asserted a same-filesystem/
  execute-bit trust rule for a libfm question that ChatGPT 5.5-high, citing the actual libfm
  source, showed was wrong). While this persists: treat a Perplexity return as provisional
  if it does not show a non-Sonar-2 model was actually used, and prefer running the same
  question through **ChatGPT** as well before acting on a technical/code-level claim. Do not
  silently drop Perplexity as a lane -- flag degraded returns back to Mètsàtron rather than
  quietly discounting them.

**Format -- output this verbatim, then stop:**

```
META-AGENT RESEARCH PROMPT [lane]:
[single-focus question -- include tool names, version numbers, and exactly what you need to determine]
```

Do not continue speculating while waiting. Do not attempt to answer the question yourself.
This applies to: architecture decisions, model capability questions, library version
edge-cases, and any situation where a 30-second web search collapses a multi-step rabbit hole.

This also applies when genuinely unsure of the best approach and synthesising from
the internet would improve the solution quality. Planning in a research lane before
executing here is cheaper than burning tokens in circles.

## Model Guidance

- Main session model cannot be changed autonomously -- use `/model sonnet|haiku` yourself.
- **The subagent tier table has ONE home: the `subagent-routing` skill** (authored in `HelmCortex/FORGE/harness/userspace/SKILLS.md`, deployed to `~/.claude/skills/` via the userspace lane, so every session sees it). Load it before spawning subagents via the Agent tool. It carries the current tier rulings — including the provisional Opus 5 entry — and supersedes any tier table previously restated here; do not re-add one, that is how drift happens.
- Standing rules that stay here: always set the `model` parameter explicitly per subagent (never default all subagents to the session model), and never silently switch model -- state which model and why, one line.
- Skill `model:` frontmatter is **BANNED in every scope** -- the key is operative in Claude Code and silently switches the executing model for the skill's turns (frontmatter pins removed in `15edb66de`; law sealed 2026-07-11 in `HelmCortex/FORGE/harness/HelmCortex/META-AGENTS.md`, with the cache law). Model hints live as inert `<!-- model -->` comment blocks in harness sources instead.

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
| Guix     | `package-guix.org`     | `.config/guix/manifests/*.scm`        | `guix:apply`, `guix:pull`         |
| Flatpak  | `package-flatpak.org`  | `linux/.flatpak/manifest/apps.ssv`    | `flatpak:apply`, `flatpak:diff`   |
| Snap     | `package-snap.org`     | `all/.snap/manifest/apps.ssv`         | `snap:apply`, `snap:diff`         |
| Pip      | `package-pip.org`      | `all/.pip/manifest/packages.ssv`      | `pip:apply`, `pip:diff`           |
| NPM      | `package-npm.org`      | `all/.npm/manifest/global.ssv`        | `npm:apply`, `npm:diff`           |
| Cargo    | `package-cargo.org`    | `all/.local/share/dotcortex/manifests/cargo/crates.ssv` | `cargo:apply`, `cargo:diff` |
| AppImage | `package-appimage.org` | `all/.appimage/inventory/all.ssv`     | `appimage:update`                 |
| Homebrew | `package-homebrew.org` | `all/.homebrew/manifest/brews.ssv`    | `brew:apply`                      |
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
- `agents-skills*.org` -- all agent skills, split by scope: base (session + universal), `-dotcortex`, `-helmcortex`, `-harness`
- `agents-hooks.org` -- Claude settings, hooks, OpenCode config, plugin manifests
- Module namespaces: `package-*`, `desktop-*`, `emacs-*`, `agents-*`, `services-*`, `sanctuary-*` (Virtual Habitat guests; engine in `sanctuary-distrobox.org`), `tools-*`, plus standalone environment modules (shell, term, mux, x11, style, fonts, icons, menu). Every root source stays under the 100 KB module budget — `org-style-lint` warns on breach; split along section seams when it fires.
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

Situational gotchas live in on-demand skills — load the relevant one rather than reading this section. See `dotcortex-gotchas` (stow, tangle, Guix), `sanctuary-gotchas` (XFCE, Xephyr, Flatpak audio, X11 ghost windows), `pi-agent-gotchas` (pi-coding-agent provider config).

## HelmCortex Integration

DotCortex (foundation) and HelmCortex (temple) are fully decoupled. DotCortex does **not** stow files into HelmCortex -- HelmCortex owns all its own configs (`.obsidian/`, `.vscode/`, FORGE/bin scripts, conda configs) directly.

DotCortex's only HelmCortex touchpoint: the shell PATH entry in `.zshenv` adding `$HOME/HelmCortex/FORGE/bin` to `$PATH` for tools like `auryn`, `helmcortex-anaconda`, and `claude-code-md-pipeline`.

HelmCortex lives at `~/HelmCortex` (may be a symlink to a mount point like `~/mnt/x230/HelmCortex`).

**Historical note**: HelmCortex configs were previously managed via `helmcortex.org` and stowed from `all/HelmCortex/`. This was decoupled in March 2026. The `style.org` laincore.css tangles directly to `~/HelmCortex/.obsidian/snippets/` (not through stow).

## Multi-Machine Setup (Star Fleet)

**System provenance for each machine lives in SystemCodex:**
=HelmCortex/CORTEX/GoldenAge_Loom/SteinerCortex/SystemCodex/Machines/=
Check there first when working on a specific machine — init system, service management, Tailscale, storage, and known quirks are documented per-machine. Update it whenever the system state changes.

- **X230** (ThinkPad, Debian/systemd): HelmCortex native, overlays: `all linux debian x230`, verb: `loom stow:x230`
- The x230 checkout of this repo lives at `/home/metsatron/DotCortex` on host `x230` (`git remote x230`).
- **T480s** (ThinkPad, Devuan/sysv-init): HelmCortex mounted + symlinked, overlays: `all linux debian devuan t480s`, verb: `loom stow:t480s`
- **T480** (ThinkPad, Vendefoul Wolf/Devuan): SSH alias `t480`, overlays: `all linux debian t480`, verb: `STOW_PKGS="all linux debian t480" make safe-stow`. **Service manager is OpenRC** (`openrc` 0.56, owns `/etc/init.d/rc`, brought up 70 services at last boot); sysvinit is only PID 1. Use `rc-service` / `rc-update`, and note both live in `/sbin` — **not** on the default user PATH, so an unqualified `rc-update` returns "command not found" and any `|| echo` check silently reports a false negative. Services register under `/etc/runlevels/`, **not** `/etc/rc*.d/` — sysv `rc*.d` links are dead letters here and will never run. Corrected 2026-07-14: this entry previously claimed "ISO says OpenRC but installed system is sysv-init — use `service`, not `rc-service`". That was wrong, and it was expensive: the guix-daemon fix was applied in the sysv idiom (an `/etc/rc2.d/S02` link plus an LSB script) which OpenRC ignores, so it was converted to native `#!/sbin/openrc-run` on 2026-07-14. That was necessary but NOT sufficient: the daemon kept dying every reboot and being hand-started — "fixed" repeatedly — until 2026-07-27, when the real recurring cause surfaced. Timestamped backups of the init script left in `/etc/init.d/` (the `cp file.backup-$(date)` reflex) are parsed by OpenRC as rival services all declaring `Provides: guix-daemon`, so it starts none at boot while `rc-service … start` by filename still works — the false positive behind months of hand-fixes. Two lessons: init-system claims must be **probed** (`ps -p 1`, `/run/openrc`, `dpkg -l openrc`), never inherited from a doc; and a correctly-registered service that still won't boot means checking `/run/openrc/deptree` for provider collisions (stray files in `/etc/init.d/`), not just re-reading the init script. Full mechanism and fix are in the `dotcortex-gotchas` skill.
  - Devuan's OpenRC has **no `localmount`** service (that is a Gentoo name; here it is `mountall.sh` / `checkroot.sh`). A `depend()` with `need localmount` makes OpenRC refuse to start the service outright. Prefer `after`, which is advisory and degrades safely.

- **T480s** (ThinkPad, Devuan): has **no OpenRC** — it is genuinely plain sysv-rc, so `/etc/rc2.d/S03…` links and `service` are correct THERE. T480 and T480s are *not* the same shape. Do not copy an init script between them.
- **S24** (Samsung Galaxy S24 Ultra, Android/Termux): SSH alias `s24`, overlays: `all termux s24`, verb: `loom stow:s24`; no Guix, use `STOW_PKGS='all termux s24' make safe-stow` if loom unavailable
- Future machines: clone DotCortex, run `INSTALL.sh`, done

### Overlay Scoping

- `all/` -- cross-platform (works on Linux, macOS, etc)
- `linux/` -- Linux-only (Guix is Linux-only, so `host-wrap` lives here)
- `debian/` -- Debian-family shared (apt/nala packages)
- `devuan/` -- sysv-init shared (non-systemd daemons, desktop launchers for XFCE panel scripts)
- `x230/` -- X230-specific (earlyoom, neofetch/fastfetch configs, GTK settings, wezterm, systemd services)
- `t480s/` -- T480s-specific (future machine-specific configs)

### .zshenv for SSH PATH

The `.zshenv` file (tangled from `shell.org`) sources Guix profiles for ALL zsh invocations (login, interactive, scripts, SSH). This ensures `emacs`, `nvim`, `guile`, and other Guix tools are available over SSH without manual PATH setup.

## When Working on DotCortex

- Always edit `.org` source, never tangled output
- The Makefile is tangled from `loom.org` -- edit `loom.org`, not Makefile
- New skills, hooks, plugins, and agent instructions are authored in `.org` files, never in emitted harness directories
- Use `make preview-stow` for a dry-run before applying
- After adding a new package manager, add loom verbs AND make targets
- When searching for a tool, check Guix profiles (`~/.guix-extra-profiles/core/core/bin/`) before assuming it's not installed
- When uncertain about external tools or APIs, issue a Perplexity research prompt rather than exploring speculatively

## Non-Claude Agent Rules

These rules apply to OpenCode, Codex, and any other non-Claude harness:

1. **Edit harness config through canonical source** -- `.claude/`, `.opencode/`, `.codex/`, and `.agents/` outputs may all be managed here, but changes must be made in the owning `.org` source and re-tangled. Do not hand-edit emitted harness files unless the user explicitly asks for that exact path.
2. **Agent config goes in the right directory** -- `.opencode/` for OpenCode-specific config, `.codex/` for Codex-specific config, `.claude/` for Claude-specific config, and `.agents/` for universal non-Claude skills. Shared doctrine may intentionally emit to multiple harness directories from one `.org` source.
3. **Skills are authored in the `agents-skills*.org` family** -- tangle to `all/.agents/skills/X/SKILL.md` for stow-global skills, `.agents/skills/X/SKILL.md` for DotCortex-scoped skills, or `.opencode/skills/X/SKILL.md` for OpenCode-exclusive skills. Do not write skill files directly. Note the stow-global lane is now nearly closed: DotCortex owns six skills, and anything about userspace or HelmCortex belongs in `HelmCortex/FORGE/harness/userspace/SKILLS.md` instead.
