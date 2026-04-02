# Session Memory (auto-updated by Opus, max 2000 chars)

## Session Facts

- `claude` binary cannot be called as subprocess from within Claude Code Bash tool — swallows stdout via IPC takeover. claude-plugins-apply must be run from a regular terminal.
- codex-plugin-cc is a Claude Code plugin, NOT an npm package. Installed via `claude plugin marketplace add openai/codex-plugin-cc` + `claude plugin install codex@openai-codex`.
- Claude Code marketplace name for openai/codex-plugin-cc is `openai-codex` (auto-derived by CLI).
- Plugin install key format: `<pkg>@<marketplace_name>` — this key appears in ~/.claude/plugins/installed_plugins.json under `plugins` map.
- codex-plugin-cc v1.0.1 at ~/.claude/plugins/cache/openai-codex/codex/1.0.1/
- /codex:rescue is the delegation command (hands task to Codex agent). /codex:review and /codex:adversarial-review are read-only.
- claude.org created — manages Claude Code plugin manifest (plugins.ssv), claude-plugins-apply, claude-plugins-health, claude.mk.

## User Model (max 1500 chars for this section)

- Expects Claude Code plugins to be declared in DotCortex for reproducibility, following SSV manifest + apply/health + .mk pattern used for other package managers.
