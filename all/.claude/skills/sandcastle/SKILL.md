---
name: sandcastle
description: Orchestrate AFK coding agents in isolated Podman/Docker sandboxes with sandcastle.run(). Covers API patterns, branch strategies, Podman preference, session resume/fork, and super system integration.
model: claude-sonnet-4-6
---

# Sandcastle

Use this skill when orchestrating AFK coding agents in isolated sandboxes, designing agent pipelines with review steps, or integrating Sandcastle into the super system.

## What It Is

`@ai-hero/sandcastle` — TypeScript library for orchestrating AI coding agents in isolated Podman/Docker/Vercel sandboxes. Provider-agnostic: one API, swappable sandbox backends.

```typescript
import { run, claudeCode } from "@ai-hero/sandcastle";
import { podman } from "@ai-hero/sandcastle/sandboxes/podman";

await run({
  agent: claudeCode("claude-sonnet-4-6"),
  sandbox: podman(),
  promptFile: ".sandcastle/prompt.md",
  maxIterations: 5,
});
```

## Sandbox Provider: Podman Preferred on This Stack

Podman is the preferred first sandbox provider on Devuan/Vendefoul because it fits the
daemonless, rootless-oriented host posture. Docker remains technically possible on
non-systemd systems but is not the default assumption for this stack. Validate Podman's
actual rootless, cgroup, networking, and socket requirements on the target host before
deployment.

```typescript
import { podman } from "@ai-hero/sandcastle/sandboxes/podman";

sandbox: podman({
  imageName: "sandcastle:myrepo",
  mounts: [
    { hostPath: "~/.npm", sandboxPath: "/home/agent/.npm", readonly: true },
  ],
})
```

`noSandbox()` for interactive/supervised sessions on the host.

## Branch Strategies

| Strategy | When |
|---|---|
| `{ type: "head" }` | Fast iteration, bind-mount only, writes directly to host CWD |
| `{ type: "merge-to-head" }` | AFK/CI: temp branch, merge back, clean up |
| `{ type: "branch", branch: "name" }` | Explicit branch, PRs, parallel fan-out |

**Parallel fan-out requires explicit `branch` strategy** — never use `head` or `merge-to-head` with `Promise.all()`.

## Core API Patterns

> Model names in examples below are illustrative — select the appropriate model per task.

### One-shot run
```typescript
const result = await run({
  agent: claudeCode("claude-sonnet-4-6"), // example — choose per task
  sandbox: podman(),
  promptFile: ".sandcastle/prompt.md",
  branchStrategy: { type: "branch", branch: "agent/task" },
  maxIterations: 5,
  completionSignal: "<promise>COMPLETE</promise>",
});
console.log(result.commits);
```

### Implement → test gate → review (single warm sandbox)
```typescript
await using sandbox = await createSandbox({
  branch: "agent/fix",
  sandbox: podman(),
  hooks: { sandbox: { onSandboxReady: [{ command: "npm install" }] } },
});
await sandbox.run({ agent: claudeCode("claude-sonnet-4-6"), promptFile: ".sandcastle/implement.md", maxIterations: 5 });
const tests = await sandbox.exec("npm test");
if (tests.exitCode !== 0) throw new Error(tests.stdout);
await sandbox.run({ agent: claudeCode("claude-sonnet-4-6"), prompt: "Review and fix." });
```

### Session resume / fork
```typescript
const first = await run({ agent: claudeCode("claude-sonnet-4-6"), sandbox: podman(), prompt: "Draft a plan" });
const second = await first.resume?.("Now implement");

// Fan-out fork (each child gets its own branch)
const [a, b] = await Promise.all([
  first.fork?.("Review migrations", { branchStrategy: { type: "branch", branch: "review-a" } }),
  first.fork?.("Audit auth", { branchStrategy: { type: "branch", branch: "review-b" } }),
]);
```

### Interactive (human-supervised, no sandbox)
```typescript
import { interactive } from "@ai-hero/sandcastle";
import { noSandbox } from "@ai-hero/sandcastle/sandboxes/no-sandbox";

await interactive({ agent: claudeCode("claude-sonnet-4-6"), sandbox: noSandbox() });
```

## Dynamic Prompt Context

Inside prompt files (not inline strings), `!`command`` runs in the sandbox and its stdout replaces the expression:

```markdown
# Open issues
!`gh issue list --state open --label Sandcastle --json number,title,body --limit 20`

# Recent commits
!`git log --oneline -10`
```

## Where It Fits in the Super System

```
Per-agent Unix user (Category B)
  ├─ Virtual Habitat rooms → persistent lived-in OS environments
  └─ Sandcastle → ephemeral task execution sandboxes
       └─ Podman container + git worktree → merge-back → cleanup
```

Sandcastle is scoped to **one task** and tears down after. Virtual Habitat rooms are **permanent** sanctuaries that agents re-enter across sessions. They are complementary, not competing.

## Setup

```bash
cd my-repo
npm install --save-dev @ai-hero/sandcastle
npx @ai-hero/sandcastle init   # prompts: provider, agent, template
cp .sandcastle/.env.example .sandcastle/.env
# fill in CLAUDE_CODE_OAUTH_TOKEN (run: claude setup-token)
npx tsx .sandcastle/main.ts
```

## Templates

| Template | Use |
|---|---|
| `blank` | Write your own prompt and orchestration |
| `simple-loop` | Pick issues one by one, close them |
| `sequential-reviewer` | Implement → review per issue |
| `parallel-planner` | Plan parallelizable issues, execute on separate branches, merge |
| `parallel-planner-with-review` | Same + per-branch review step |

## Notes for This Stack

- **Podman over Docker** — preferred on Devuan/sysv-init hosts; validate actual requirements before deployment
- **Target policy** — once per-agent Unix users are stable, the owning agent user should launch its Sandcastle sandboxes
- **Candidate mount policy** — selected DotCortex/Guix projections may be bind-mounted read-only only after a dedicated validation pass defines the permitted paths
- **Session capture** — for Claude Code runs, Sandcastle captures resumable session JSONL under Claude Code's host session layout. Other providers use provider-specific session locations. Treat session capture, retention, and export paths as provider-specific.

## Credentials and Secrets

- `.sandcastle/.env` is local-only — must be ignored by Git.
- Never commit, log, export, print, or copy OAuth tokens, API keys, cookies, or credential
  files into worktrees, prompts, session exports, images, or bind mounts.
- Do not use `copyToWorktree` for secret-bearing files.
- Mount only the minimum required credential material, scoped to the specific sandbox run,
  after explicit review.
