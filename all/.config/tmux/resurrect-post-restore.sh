#!/usr/bin/env bash
#!/usr/bin/env bash
# Post-restore hook for tmux-resurrect
# Checks for recent claude/opencode sessions and notifies user

CLAUDE_SESSIONS="$HOME/.claude/projects"
if [ -d "$CLAUDE_SESSIONS" ]; then
  latest=$(find "$CLAUDE_SESSIONS" -name "*.jsonl" -mmin -720 -type f 2>/dev/null | head -1)
  if [ -n "$latest" ]; then
    tmux display-message "Claude Code sessions available. Use 'claude --resume' to restore."
  fi
fi
