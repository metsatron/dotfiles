---
name: meta-agent
description: Drive delegated agents (Codex on X230, Haiku subagents, local builds); scope, dispatch, verify, gate commits so the human never has to touch the burning tools.
---

# Meta-Agent Orchestration

Drive delegated agents as a supervising meta-agent: decompose work, write handoffs, dispatch, verify, gate commits. The human talks only to you; you drive the tools so they never have to.

## Delegation model — who does what

- **Haiku (`claude-haiku-4-5`) / GPT-5.4-mini** — mechanical, high-volume, zero-ambiguity: enumeration, file ops, per-item classification against a fixed taxonomy. Spawn via the Agent tool with `model: haiku`.
- **Sonnet subagents (background, parallel)** — sweep/verify/diagnose lanes: triage reports, corpus inventories, regression checks, reconciliation analyses, network/device identification. Proven pattern 2026-07-10: fan several out simultaneously at session start, keep the main thread for decisions and commit gates.
- **Opus subagents** — client-production passes and anything multi-machine with rebuild/deploy consequences; give them the client profile, the ordered plan, hard rules (never `down -v`, adapt-and-report on discrepancy, stop on genuine risk), and demand a per-step evidence report.
- **Codex gpt-5.6-luna** — building: generators, reconstructors, real tooling from written specs (lineage: five clean gpt-5.5 builds 2026-07-10). GPT-5.6 shipped on ChatGPT-account Codex 2026-07-11 (live-probed: luna at high and xhigh both accepted). Ruling 2026-07-11: default `gpt-5.6-luna` cranked high/xhigh — Luna at max effort is still cheaper than `gpt-5.6-terra`, so Terra is cost/perf-dominated and skipped; `gpt-5.6-sol` for the hardest passes (top tier, cheaper than Opus even at max); `gpt-5.5` remains the known-good fallback if 5.6 misbehaves. See Codex-on-X230 and Local Codex.
- **You (Opus/Sonnet/Fable)** — design, TaskHandoff authoring, verification against spec, commit gating.

## Fan-out playbook (sealed from the 2026-07-10 relay)

- Dispatch exploration/verification subagents in the background FIRST, then do main-thread reads while they run; bundle every decision that surfaces into ONE AskUserQuestion so the human answers once while agents keep working.
- Verification briefs must demand a VERDICT line (RESOLVED / STILL-REPRODUCES / SURVIVED-CLEAN / CANNOT-SAFELY-TEST) plus an evidence chain; tick ledgers only from evidence, quoting it in the tick.
- Honest-accounting briefs: tell build agents explicitly to refuse to fabricate (report gaps as gaps, use the spec's own fallback values, never invent filler); this is what makes their output trustable unreviewed.
- Reconcile-then-execute for possibly-superseded specs: the agent first checks whether shipped reality already satisfies the spec, and executes only on a clean (c)-unshipped verdict — surfacing the conflict IS the deliverable otherwise.
- Remote fleet commands in subagent prompts must use `/usr/bin/ssh` — bare `ssh` resolves to the kitty SSH kitten in tool subprocesses and dies without a TTY.

## Codex-on-X230 recipe — the ONLY reliable way to have Codex write HelmCortex

Learned 2026-07-08 through three failures: **Codex cannot write the NFS-mounted HelmCortex on T480s** — its bubblewrap sandbox can't govern an NFS mount even at `danger-full-access`. **X230's HelmCortex is local ZFS**, so run Codex there. X230's bwrap is also broken (`RTM_NEWADDR: Operation not permitted` on the loopback netns, re-confirmed 2026-07-10), so bypass the sandbox. The bypass flag needs Mètsàtron to name it per session — the harness classifier blocks it otherwise. Naming "Codex on the X230" generally does NOT count (proven 2026-07-10: the auto-mode classifier denied the dispatch anyway) — either he names the flag itself, or dispatch outside auto mode so he can take the permission prompt; stage the task prompt file first either way, so the lane is one approval from live.

1. Write the task prompt to the SHARED repo (T480s writes `~/mnt/x230/HelmCortex/…`, X230 reads it locally) — avoids SSH quoting:
   `Write ~/mnt/x230/HelmCortex/ROOTS/PromptGolf/_recon/<task>.md`
2. Dispatch over SSH, in the background:
   ```
   /usr/bin/ssh x230 'cd ~/HelmCortex && codex exec --model gpt-5.6-luna -c model_reasoning_effort=xhigh \
     --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
     "$(cat ROOTS/PromptGolf/_recon/<task>.md)" > ROOTS/PromptGolf/_recon/<task>-codex.log 2>&1'
   ```
3. The bypass flag runs codex UNSANDBOXED with auto-approve. Only acceptable because X230 is trusted, the target is a git repo (reviewable/revertable), and the task is tightly bounded. ALWAYS scope the prompt with HARD CONSTRAINTS: only these files; no commit/push/rm/destructive commands; never write LOGS/ or the KeePass databases in NEXUS/.

## Codex concurrency — SERIAL LAW (sealed 2026-07-10)

- **One unsandboxed Codex per repo at a time, no exceptions.** Two concurrent X230 jobs destroyed each other's work: job B took its status baseline before job A finished, mis-attributed A's fresh edits to its own accidental side effect, and "helpfully" reverted them via git checkout. Bypass mode has no approval gate on checkout.
- Every Codex prompt (bypass or sandboxed) MUST carry the never-tidy clause: "the worktree has pre-existing dirt from concurrent lanes — do NOT touch, restore, checkout, or clean ANY file you did not yourself edit, even if the tree looks messy."
- **Verify results on disk, never by report alone.** A Codex self-report can be true at write time and stale minutes later in a multi-writer repo — grep the actual file content and `git status` the target paths yourself before committing anything.

## Verify unsandboxed Codex stayed in scope (MANDATORY)

- `git status --short` in full (Codex may self-report only a path-limited status — do not trust it).
- Compare mtimes: `stat -c '%y %n'` the intended files (Codex-run window) vs any suspect dirty files. Anything modified BEFORE the run window is pre-existing, not Codex.
- Re-run the tool Codex produced, yourself, to confirm it works.
- Version pins Codex chooses must be fleet-proven: check the live elevated install with `importlib.metadata.version("<dist>")` (`pip show` misses dist-name mismatches) and correct the pin before committing. Better: put the proven version in the prompt.

## Commit discipline on multi-writer repos (temple X230, NFS HelmCortex, DotCortex)

These repos routinely have LIVE concurrent sessions staging and committing. Sealed 2026-07-10 after two real collisions:

- NEVER bulk-commit. Before any commit, check the staged index for other lanes' work: `git diff --cached --quiet` — a pre-loaded index rides into a bare `git commit` silently (a services commit swept 14 staged files from a rofi/xfce lane; repaired via `git reset --soft HEAD~1` + pathspec recommit).
- Prefer pathspec commits (`git commit -m … -- <paths>`): they commit those paths' worktree state and leave every other lane's staged entries untouched. Caveat: pathspec commits cannot include untracked files — `git add` them first.
- A live `.git/index.lock` is never deleted: identify the holder (`pgrep -af git`, check both machines), then wait for no-lock AND empty index before committing — a background waiter loop (`[ ! -f .git/index.lock ] && git diff --cached --quiet`) queues your commit safely behind theirs.
- Your uncommitted file edits can be swept into ANOTHER session's commit (it happened to two TODO ticks) — before re-editing or assuming loss, `git log --oneline -3 -- <path>`.
- If your intended file is entangled with another lane's hunks (staged + unstaged in one file), commit the clean half and LEDGER the entangled half explicitly (which hunks, whose lane, when to commit) — an applied-but-uncommitted change the ledgers know about is fine; one they don't is how work gets lost.

## Local Codex on T480s — sandboxed lane for local-disk repos (DotCortex)

- **LEAD RULE — never route DotCortex codex work through the `codex:codex-rescue` Agent type.** It pins `--sandbox workspace-write` to the *Claude session's* workspace, so the target repo is read-only and the job **silently no-ops at apply time** — zero edits, yet it returns a confident diagnosis and leaves a dead `running` job behind. This has burned three sessions (the "have you even sent out a single fucking sub agent?!" no-ops were this, not codex failing). "luna" = the model `gpt-5.6-luna`. Drive it DIRECTLY via Bash from the repo dir, one Codex per repo (serial law below), and VERIFY the `git diff` yourself before reporting — a green Codex exit proves nothing.
- Verified-good DotCortex invocation (T480s, this box): `export PATH=~/.npm-global/bin:$PATH; cd ~/DotCortex && codex exec --model gpt-5.6-luna -c model_reasoning_effort=high --sandbox workspace-write --skip-git-repo-check "$(cat <prompt-file>)"`. Codex `~/.codex/config.toml` marks `/home/metsatron/DotCortex` a trusted project, so the cwd repo is writable under `workspace-write` even though `sandbox_workspace_write.writable_roots` lists only HelmCortex (those are *extra* roots; the cwd project is always writable). No bypass flag, no per-session authorization needed for DotCortex.
- DotCortex is local ext4, and T480s bwrap works: `cd ~/DotCortex && codex exec --model gpt-5.6-luna -c model_reasoning_effort=xhigh --sandbox workspace-write --skip-git-repo-check "$(cat <prompt>)"` builds safely with NO bypass flag and no per-session authorization. It reads NFS HelmCortex fine (corpus reads); it just can't write it.
- **Plugin trap 1 — false "not installed":** the codex-rescue companion may claim "Codex CLI is not installed"; the binary lives at `~/.npm-global/bin/codex` (npm lane, `package-npm.org`). That is a PATH bug in the companion's environment — drive codex directly via Bash with `PATH=~/.npm-global/bin:$PATH`.
- **Plugin trap 2 — workspace pinning:** the companion pins `--sandbox workspace-write` cwd to the CLAUDE SESSION's workspace, so a DotCortex-targeted job dispatched from a HelmCortex session gets a read-only DotCortex and fails at apply time (it will still produce a good diagnosis). Direct `codex exec` from the target repo's directory is the reliable path.
- The companion also leaves dead jobs flagged `running`, blocking later dispatches. Reap in `~/.claude/plugins/data/codex-openai-codex/state/<ws>/jobs/`: set the stale `running` job (pid dead) to `failed` in both `state.json` and the job JSON, with backups. (Pid-liveness fix is ledgered in TODO DotCortex.)
- Codex is weak at interlocution and burns the user — that is WHY this layer exists. Drive it; never route the user to it.

## TaskHandoff shape

Structured handoffs, not prose essays (schema: `FORGE/harness/HelmCortex/META-AGENTS.md` § TaskHandoff Protocol). Verified `working_directory`; `allow_git: stage_only` by default; explicit `allowed_paths`; `forbidden_paths` always include LOGS/ (NEXUS/ holds only encrypted KeePass databases and repo mirrors since the 2026-07-11 migration — readable, but the databases are never write targets); explicit `stop_conditions`.

A diagnosed-but-unapplied Codex run is not waste: re-dispatch the apply with the diagnosis baked into the prompt (root cause + exact proposed diff) — the second run is fast and surgical.
