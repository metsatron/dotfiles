# /prime — DotCortex Orientation

Orient yourself in the DotCortex literate dotfiles system. Optionally scoped: $ARGUMENTS

## Steps

### Always (unscoped `/prime`)

1. Read the top-level directory structure: `ls ~/DotCortex/`
2. Read recent history: `git log --oneline -15`
3. Check current state: `git status`
4. Read auto-memory files from `.claude/projects/*/memory/` — scan MEMORY.md index, then read relevant memory files
5. Check for recent handoffs: `ls -t ~/HelmCortex/LOGS/handoffs/ | head -3` — if any exist within the last day, read the most recent one

Then output a brief orientation (5-10 lines max) covering:
- What branch you're on and its state
- What work appears in-progress
- Key context from memory/handoffs
- Ask what to work on

### Scoped (`/prime emacs`, `/prime shell`, `/prime flatpak`, `/prime loom`)

Do everything above, PLUS:

1. Read the matching org source file:
   - `emacs` -> `emacs.org`
   - `shell` -> `shell.org`
   - `flatpak` -> `flatpak.org`
   - `loom` -> `loom.org`
   - `style` -> `style.org`
   - `tools` -> `tools.org`
   - Any other scope -> try `SCOPE.org`

2. Include scope-specific orientation in your summary

## Rules
- Do NOT read file contents beyond what's listed above — load just-in-time, not just-in-case
- Keep orientation output concise — this is a launchpad, not a survey
- Remember: never edit tangled output, always edit .org source
- The Makefile is tangled from loom.org — never edit it directly
