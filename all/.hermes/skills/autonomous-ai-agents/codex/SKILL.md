---
name: codex
description: Delegate coding tasks to OpenAI Codex CLI. Use for building features, refactoring, and automated code changes via stdin pattern.
version: 2.0.0
metadata:
  hermes:
    model_primary: gpt-5.4
    model_fast: gpt-5.4-mini
    tags: [Coding-Agent, OpenAI, Codex, CLI, Automation]
    related_skills: [claude-code, opencode, hermes-agent]
    required_commands: [codex]
---

# Codex CLI — Non-interactive Agent

Delegate coding tasks to OpenAI Codex via stdin pattern. Best for single-shot, scriptable automation.

## Binary

`/home/metsatron/.npm-global/bin/codex`

## Model Selection

- Primary: `gpt-5.4`
- Fast: `gpt-5.4-mini`

Use `-c model="gpt-5.4"` or `-c model="gpt-5.4-mini"` to select.

## Prerequisites

- OpenAI API key in `~/.codex/config.toml` or environment variable
- Git repository (or `--skip-git-repo-check` for non-git directories)

## Non-interactive Pattern

```bash
codex exec - --full-auto --skip-git-repo-check --json <<< "PROMPT_HERE"
```

### Components:
- `exec -`: Run exec command, read prompt from stdin (`-` or pipe)
- `--full-auto`: Fully autonomous mode (no approval prompts)
- `--skip-git-repo-check`: Bypass git repository requirement
- `--json`: JSON output format for structured parsing

## Exec Command Options

| Flag | Purpose |
|------|---------|
| `-c, --config <key=value>` | Override config value (dotted path) |
| `--enable <FEATURE>` | Enable feature |
| `--disable <FEATURE>` | Disable feature |
| `--quiet` | Reduce output verbosity |
| `--approval-mode <MODE>` | Set approval mode (e.g., suggest) |
| `--model <MODEL>` | Specify model |

## Usage Examples

```bash
# Basic non-interactive execution
codex exec - --full-auto --skip-git-repo-check --json <<< "Refactor auth module for JWT"

# With custom config (model selection)
codex exec - --full-auto --skip-git-repo-check --json -c model="gpt-5.4" <<< "Write unit tests"

# With approval mode (suggest only)
codex exec - --full-auto --skip-git-repo-check --json --approval-mode suggest <<< "Review this code"

# Pipe content from file
cat src/auth.py | codex exec - --full-auto --skip-git-repo-check --json <<< "Add error handling"

# With quiet mode
codex exec - --full-auto --skip-git-repo-check --json --quiet <<< "Update docs"
```

## Output Format (JSON)

When using `--json`, output includes:
- `stdout`: Primary output
- `stderr`: Error messages
- `return_code`: Exit code (0 = success)

Parse with: `jq -r '.stdout'` or similar JSON tool.

## Pitfalls

- **Must use `--skip-git-repo-check`** for non-git directories
- **JSON mode required** for programmatic parsing
- **Stdin pattern only**: Use `<<<` or pipe (`|`), not direct prompt argument
- **API key required**: Set in `~/.codex/config.toml` or `OPENAI_API_KEY`

## Security

`--full-auto` grants full tool access; use only in trusted environments or sandboxes.

## Related

For interactive sessions, run `codex` directly.
