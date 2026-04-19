---
name: opencode-telegram
description: Operate the opencode-telegram-bot — Telegram client for OpenCode CLI, mobile coding task management with scheduled tasks.
---

# OpenCode Telegram Bot

Use this skill when operating the opencode-telegram-bot for mobile OpenCode task management.

## What It Is

Telegram bot that wraps OpenCode CLI — run and monitor AI coding tasks from your phone. Everything runs locally on your machine. Includes scheduled tasks support as a lightweight OpenClaw alternative.

- **Upstream:** https://github.com/grinev/opencode-telegram-bot
- **Package:** `@grinev/opencode-telegram-bot`
- **Config:** `~/.config/opencode-telegram-bot/.env`
- **Runtime requires:** `opencode serve` running on `http://localhost:4096`

## Prerequisites

1. **Telegram Bot Token** — Create via [@BotFather](https://t.me/BotFather): send `/newbot`, follow prompts
2. **Telegram User ID** — Send any message to [@userinfobot](https://t.me/userinfobot), reply shows your numeric ID
3. **Node.js 20+** — The bot runs on Node
4. **OpenCode serve running** — The bot connects to `http://localhost:4096`

## Quick Start

```bash
# 1. Ensure opencode serve is running
opencode serve

# 2. Start the bot (first run launches config wizard)
opencode-telegram start

# 3. Reconfigure at any time
opencode-telegram config
```

Or via npx (avoids global install):
```bash
npx @grinev/opencode-telegram-bot
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/status` | Server health, current project, session, model info |
| `/new` | Create a new session |
| `/abort` | Abort the current task |
| `/sessions` | Browse and switch between recent sessions |
| `/projects` | Switch between OpenCode projects |
| `/rename` | Rename the current session |
| `/commands` | Browse and run custom commands |
| `/task` | Create a scheduled task |
| `/tasklist` | Browse and delete scheduled tasks |
| `/opencode_start` | Start OpenCode server remotely |
| `/opencode_stop` | Stop OpenCode server remotely |
| `/help` | Show available commands |

## Environment Variables

The bot stores config at `~/.config/opencode-telegram-bot/.env`:

| Variable | Required | Default |
|----------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | — |
| `TELEGRAM_ALLOWED_USER_ID` | Yes | — |
| `OPENCODE_API_URL` | No | `http://localhost:4096` |
| `OPENCODE_MODEL_PROVIDER` | Yes | `opencode` |
| `OPENCODE_MODEL_ID` | Yes | `big-pickle` |
| `BOT_LOCALE` | No | `en` |
| `TASK_LIMIT` | No | `10` |
| `STT_API_URL` | No | — |
| `STT_API_KEY` | No | — |

## Scheduled Tasks

Create with `/task`, manage with `/tasklist`. Useful for periodic code maintenance or prompts to run while away. Max 10 tasks by default (`TASK_LIMIT`).

## Security

Strict user ID whitelist — only `TELEGRAM_ALLOWED_USER_ID` can interact. No open ports beyond Telegram Bot API.

## DotCortex Integration

The package is tracked in `npm.org` manifest (`@grinev/opencode-telegram-bot`). Config file (`~/.config/opencode-telegram-bot/.env`) is gitignored — contains bot token and user credentials.

## Health Check

```bash
# Verify bot is running
ps aux | grep opencode-telegram

# Check opencode serve is active
ps aux | grep "opencode serve"

# Verify Node environment
node --version  # needs 20+
```
