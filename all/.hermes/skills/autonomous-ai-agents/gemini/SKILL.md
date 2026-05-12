---
name: gemini
description: Delegate coding tasks to Gemini CLI. Use for feature implementation, review, refactoring, and one-shot headless tasks.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    model_primary: gemini-2.5-pro
    model_fast: gemini-2.5-flash
    tags: [Coding-Agent, Gemini, Google, CLI, Automation]
    related_skills: [agent-orchestrator, claude-code, codex, opencode]
    required_commands: [gemini]
---

# Gemini CLI — Non-interactive Agent

Delegate coding, review, and synthesis tasks to the Gemini CLI. Use the explicit binary path below so the skill does not depend on PATH state.

## Binary

`/home/metsatron/.npm-global/bin/gemini`

## Authentication

Authenticate once with `gemini login`. Confirm the session with `gemini auth status` before using the CLI for work that depends on Google login state.

## Model Selection

- Primary: `gemini-2.5-pro`
- Fast: `gemini-2.5-flash`

Choose the model with `--model` when a task needs a specific capability.

## Non-Interactive Pattern

Use `gemini run` for headless tasks. If your local build only exposes prompt flags, the equivalent form is `gemini -p`.

```bash
gemini run --model gemini-2.5-pro --output-format json "Write unit tests for src/auth.ts"
gemini run --model gemini-2.5-flash --output-format json "Summarize this diff"
```

## Common Flags

| Flag | Purpose |
|------|---------|
| `--model <model>` | Override the model for the task |
| `--output-format json` | Emit structured output for parsing |
| `--approval-mode plan` | Read-only planning mode |
| `--approval-mode auto_edit` | Auto-approve edit tools |
| `--approval-mode yolo` | Auto-approve all tools |
| `--resume latest` | Resume the latest session |
| `--list-sessions` | List available sessions |
| `--include-directories` | Add extra workspace roots |
| `--sandbox` | Run in sandbox mode |

## Common Usage Patterns

```bash
# Code review
gemini run --model gemini-2.5-pro --output-format json "Review this change for bugs and regressions"

# Quick search or triage
gemini run --model gemini-2.5-flash --output-format json "Find the file that owns the auth flow"

# Refactor or implementation
gemini run --model gemini-2.5-pro --output-format json "Implement this change in src/auth.ts"

# Resume a previous session
gemini --resume latest
```

## YOLO Mode for Automation

Use `--approval-mode yolo` for fully automated tasks where you want to auto-approve all tool calls without prompts. This is useful for:

- Git operations (commit, push)
- Scripted workflows  
- Batch processing

```bash
gemini run --approval-mode yolo --output-format json "Commit all staged changes with conventional message"
```

**WARNING**: YOLO mode bypasses all safety checks. Only use in trusted environments or with externally sandboxed processes.

### Automated Git Workflow Example

```bash
# 1. Stage changes
git add skills.org

# 2. Commit with Gemini YOLO
gemini run --approval-mode yolo \
  --output-format json \
  "Commit staged changes with message: feat(tools): add tangle and loom skills"
```

## Rate Limits and Retries

Gemini CLI automatically retries when you hit rate limits:

```
Attempt 1 failed: You have exhausted your capacity on this model. 
Your quota will reset after 2s.. Retrying after 5394ms...
```

The CLI handles retries automatically with exponential backoff. No special handling needed - the request will succeed once quota resets.

**Best Practice**: For quick tasks that might hit limits, use `gemini-2.5-flash` which has higher rate limits.

```bash
# Fast model for quick commits
gemini run --model gemini-2.5-flash --approval-mode yolo \
  "Stage and commit skills.org changes"
```

## Pitfalls

- `gemini login` is required before the first meaningful use
- `--output-format json` is the safest choice when another tool needs to parse the result
- Keep interactive work in the TUI; use `gemini run` for one-shot tasks
