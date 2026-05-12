---
name: opencode
description: Delegate coding tasks to OpenCode CLI. Use for multi-provider coding sessions, serve mode automation, and bot-integrated task execution.
version: 1.0.0
metadata:
  hermes:
    tags: [Coding-Agent, OpenCode, CLI, Multi-Provider, Automation]
    related_skills: [codex, claude-code, hermes-agent]
    required_commands: [opencode]
---

# OpenCode — Non-interactive Agent

Delegate coding tasks to OpenCode via CLI or serve mode. Supports multiple AI providers, structured tool use, and persistent sessions.

## Binary

`/usr/local/bin/opencode`

## Prerequisites

- Provider API key in `~/.config/opencode/config.json` or environment

## Serve Mode (recommended for automation)

```bash
opencode serve                    # starts on http://localhost:4096
```

Required for `opencode-telegram-bot` and other bot integrations.

## CLI Patterns

```bash
# Run a task (fresh session)
opencode run "PROMPT_HERE"

# Specify model
opencode run --model anthropic/claude-sonnet-4-6 "Refactor auth module"

# Continue an existing session
opencode run --session SESSION_ID "Add error handling"

# Non-interactive with output
opencode run --no-interactive "Write unit tests" > output.txt
```

## Session Management

```bash
opencode sessions                 # list sessions
opencode sessions new             # create session
opencode sessions show SESSION_ID # show session details
```

## Config

```bash
opencode config                   # interactive config wizard
opencode config set model openai/gpt-5.4
opencode config set provider openai
```

## Supported Providers

- Anthropic: `anthropic/claude-*`
- OpenAI: `openai/gpt-*`, `openai/o*`
- Local via Ollama or LM Studio

## Pitfalls

- `opencode serve` must be running before bot integrations can connect
- Model strings use `provider/model-id` format — not bare model names
- Session state persists across calls; omit `--session` for a fresh context

## DotCortex Integration

Package tracked in `npm.org` (`opencode-ai`). Config at `~/.config/opencode/config.json`.
