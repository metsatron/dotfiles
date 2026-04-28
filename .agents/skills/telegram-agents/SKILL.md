---
name: telegram-agents
description: Manage Telegram-connected AI agents across machines — enable/disable, switch hosts.
model: claude-haiku-4-5-20251001
---

# Telegram Agents Manager

Use this skill when managing Telegram-connected AI agents across multiple machines.

## What It Is

A multi-machine agent management system that lets you enable/disable Telegram agents per machine and switch between machines without conflicts.

## Core Commands

```bash
# List all known agents and configured hosts
telegram-agent-host list

# Show current host, enabled agents, and running processes
telegram-agent-host status

# Enable an agent on this machine
telegram-agent-host enable <agent>

# Disable an agent on this machine
telegram-agent-host disable <agent>

# Sync configs from DotCortex
telegram-agent-host sync

# Start all enabled agents on this machine
telegram-agent-host start

# Stop all agents
telegram-agent-host stop

# Switch to another machine (stops local, starts remote via SSH)
telegram-agent-host switch <target-machine>

# Bring agents to this machine (stops remote, starts local)
telegram-agent-host bring
```

## Available Agents

| Agent | Description |
|-------|-------------|
| opencode | OpenCode + Telegram bot |
| claudecode | Claude Code desktop |
| hermes | Hermes agent (not yet installed) |
| codex | OpenAI Codex |
| pi-agent | Pi Coding Agent |

## Hosts Configuration

The file `all/.telegram-agents/hosts.conf` defines which agents run on which machines:

```
thinkpad-t480s|opencode|t480s
thinkpad-x230|opencode,hermes|x230
```

Format: `hostname|enabled_agents|ssh_alias_to_reach_this_host`

## Switching Machines

```bash
# Switch to X230 (stops T480s agents, starts X230 agents via SSH)
telegram-agent-host switch thinkpad-x230

# Switch to T480s
telegram-agent-host switch thinkpad-t480s

# Bring agents to current machine (stops remote agents, starts locally)
telegram-agent-host bring
```

## Prerequisites for Remote Switching

1. SSH config must have the ssh_alias defined (e.g., `x230` in `~/.ssh/config`)
2. Target machine must have `telegram-agent-host` and `telegram-agent-remote-start` installed
3. Target machine must have agent configs synced

## Sync to X230

```bash
telegram-agent-sync-x230
```

This syncs hosts.conf and telegram bot credentials to X230.
