---
name: agent-orchestrator
description: Hermes-native orchestration that checks ai-usage --json before selecting Codex, Claude Code, Gemini, or OpenCode models and commands.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    model_primary: claude-sonnet-4-6
    model_fast: claude-3.5-haiku
    tags: [Orchestration, Agent-Selection, Quota-Management, Cost-Control, Automation]
    related_skills: [codex, claude-code, gemini, opencode]
    required_commands: [ai-usage, jq, codex, claude, gemini, opencode]
---

# Agent Orchestrator

Use this skill when you are choosing which autonomous agent to invoke and which model to use. You are already inside Hermes, so do not tell the user to "delegate to Hermes" or hand the decision back to Hermes.

## Rule Zero

Check quota first. Run `ai-usage --json` before selecting a provider. If the quota data is unavailable, stop and ask rather than guessing.

## How To Read `ai-usage --json`

`ai-usage --json` returns a JSON array. Each item has at least:

- `provider`
- `state`
- `summary`
- `raw`

Treat a provider as surplus when:

- `state` is `ok`
- the relevant usage window exists
- the used percentage is below the task threshold

Useful selectors:

```bash
# List provider state and summary
ai-usage --json | jq -r '.[] | "\(.provider)\t\(.state)\t\(.summary)"'

# Find providers with surplus room for write/code tasks
ai-usage --json | jq -r '
  .[]
  | select(.state == "ok")
  | select((.raw.usage.primary.usedPercent // .raw.usage.secondary.usedPercent // 101) < 80)
  | .provider
'

# Relax the threshold for quick tasks
ai-usage --json | jq -r '
  .[]
  | select(.state == "ok")
  | select((.raw.usage.primary.usedPercent // .raw.usage.secondary.usedPercent // 101) < 90)
  | .provider
'
```

If you need to inspect a single provider, filter by name:

```bash
ai-usage --json | jq '.[] | select(.provider == "codex")'
ai-usage --json | jq '.[] | select(.provider == "claude")'
ai-usage --json | jq '.[] | select(.provider == "gemini")'
```

## Selection Policy

Use the first provider with surplus quota for the task type.

### Writes and Code Generation

Prefer `gpt-5.4` when `codex` has surplus quota.
If OpenAI is not available, fall back to `claude-sonnet-4-6` when `claude` has surplus quota.

### Quick and Simple Tasks

Prefer `gpt-5.4-mini` when `codex` has surplus quota.
If OpenAI is not available, fall back to `claude-3.5-haiku` when `claude` has surplus quota.

### Secondary Fallbacks

If both primary providers are saturated, choose the next healthy provider only if the task is lightweight or exploratory. Otherwise ask the user to wait or retry after quota resets.

## Common Task Patterns

### Commit

Use a quick model to summarize staged changes and draft the commit message.

- Preferred: `gpt-5.4-mini`
- Fallback: `claude-3.5-haiku`
- Escalate if the diff spans many files or behavior changes are unclear

### Review

Use a full model for multi-file review, security checks, or behavioral analysis.

- Preferred: `gpt-5.4`
- Fallback: `claude-sonnet-4-6`
- Use a quick model only for a fast first pass

### Write

Use a full model for code generation, refactors, and implementation work.

- Preferred: `gpt-5.4`
- Fallback: `claude-sonnet-4-6`

### Search

Use a quick model for file discovery, triage, and narrow lookup tasks.

- Preferred: `gpt-5.4-mini`
- Fallback: `claude-3.5-haiku`

## Invocation Templates

```bash
# Codex for writes and refactors
codex exec - --full-auto --skip-git-repo-check --json -c model="gpt-5.4" <<< "PROMPT"

# Claude Code for writes and refactors
claude -p "PROMPT" --model claude-sonnet-4-6 --output-format json

# Codex for quick tasks
codex exec - --full-auto --skip-git-repo-check --json -c model="gpt-5.4-mini" <<< "PROMPT"

# Claude Code for quick tasks
claude -p "PROMPT" --model claude-3.5-haiku --output-format json
```

## Rules

- Do not mention Hermes as a separate thing to delegate to; Hermes is the host context.
- Do not select a model before checking `ai-usage --json`.
- Prefer the least expensive model that still fits the task.
- Re-check quota before long-running or multi-stage work.
- If the task is simple, stay on the quick path unless the quota picture changes.
- If the task is a write or code generation task, favor `gpt-5.4` or `claude-sonnet-4-6` based on availability.
