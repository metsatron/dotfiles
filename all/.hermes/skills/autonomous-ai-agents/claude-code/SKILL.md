---
name: claude-code
description: Delegate coding tasks to Claude Code CLI. Use for building features, refactoring, and code analysis via non-interactive print mode.
version: 1.0.0
metadata:
  hermes:
    model_primary: claude-sonnet-4-6
    model_fast: claude-haiku-4-5-20251001
    tags: [Coding-Agent, Anthropic, Claude, CLI, Automation]
    related_skills: [codex, opencode, hermes-agent]
    required_commands: [claude]
---

# Claude Code — Non-interactive Agent

Delegate coding tasks to Claude Code CLI. Best for single-shot coding, editing, and analysis tasks via print mode.

## Binary

`/home/metsatron/.local/bin/claude`

## Prerequisites

- Anthropic API key: `ANTHROPIC_API_KEY` env or `claude auth login`

## Non-interactive Pattern

```bash
claude -p "PROMPT_HERE" --output-format json
```

### Flags

| Flag | Purpose |
|------|---------|
| `-p, --print` | Print mode — non-interactive, exits after one response |
| `--output-format <fmt>` | `text` (default) or `json` |
| `--model <model>` | Model ID (e.g., `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`) |
| `--max-turns <n>` | Limit agentic turns |
| `--allowedTools <list>` | Comma-separated list of allowed tools |
| `--system-prompt <text>` | Override system prompt |

## Usage Examples

```bash
# Basic non-interactive
claude -p "Explain what this function does" --output-format json < src/auth.py

# With model selection
claude -p "Refactor for clarity" --model claude-sonnet-4-6 < src/auth.py

# Read-only analysis (restrict tools)
claude -p "Review for security issues" --allowedTools "Read,Grep,Glob" --output-format json

# With turn limit
claude -p "Write unit tests" --max-turns 5

# Pipe content
cat src/auth.py | claude -p "Add type annotations"
```

## Output Format (JSON)

```json
{ "type": "result", "result": "...", "cost_usd": 0.001 }
```

Parse with: `jq -r '.result'`

## Pitfalls

- Print mode (`-p`) exits after one response — use `--max-turns` for multi-step tasks
- Without `--allowedTools`, Claude Code has full filesystem and shell access
- API key must be set before first use
