# /handoff — Session Summary for Fresh Windows

Generate a handoff document capturing this session's state, then write it to a file so a fresh Claude Code window can pick up where we left off with minimal context.

## Steps

1. **Gather session state:**
   - Review conversation for work done, decisions made, commits created
   - Run `git log --oneline -10` to capture recent commits
   - Run `git status` to capture in-progress work
   - Run `git diff --stat` to see uncommitted changes

2. **Write the handoff file** to: `~/HelmCortex/LOGS/handoffs/YYYY-MM-DD-HHMMSS.md`

   Use this structure:

   ```markdown
   # Handoff — YYYY-MM-DD HH:MM

   ## Work Completed
   - [bullet points of what was done]

   ## Commits This Session
   - [hash: message for each commit]

   ## Decisions Made
   - [key decisions and reasoning]

   ## Open Threads
   - [unfinished work, pending decisions, next steps]

   ## Key Files Touched
   - [file paths with brief state notes]

   ## Uncommitted Changes
   - [git status summary, or "clean"]

   ## Session Notes
   - [context worth carrying forward]
   ```

3. **Update DotCortex TODO** at `~/HelmCortex/LOGS/TODO/DotCortex.md` with session progress.

4. **Output the file path** so the user can reference it in a fresh window.

## Usage in Fresh Window
The user will open a new Claude Code session and say something like:
"Read LOGS/handoffs/2026-03-17-143022.md and continue from there."

## Rules
- Keep it under 100 lines — this is a summary, not a transcript
- Focus on what a fresh session NEEDS to know, not everything that happened
- Suggest `/commit` first if there are uncommitted changes worth preserving
