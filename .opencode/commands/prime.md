# prime - DotCortex Orientation

Use this at the start of a fresh DotCortex session to orient quickly without overloading context.

## Base Steps

1. Read the top-level repo structure
2. Read recent history with `git log --oneline -15`
3. Check current state with `git status --short`
4. Read `AGENTS.md` and `.opencode/AGENTS.md` if not already active
5. Check recent handoffs if any exist in a future `LOGS/handoffs/` or equivalent working notes location

Then produce a short orientation covering:

- current branch and worktree state
- likely work in progress
- relevant repo constraints
- the next thing to work on
- whether the requested work looks like a plan-first change

## Scoped Prime

When the user primes a scope, load only the relevant local docs:

- `flatpak` or `packages` -> `.opencode/skills/dotcortex-package-manifests/SKILL.md`
- `bootstrap` or `install` -> `.opencode/skills/dotcortex-bootstrap/SKILL.md`
- `loom`, `stow`, or `tangle` -> `.opencode/skills/dotcortex-loom/SKILL.md`
- `tangle-one` -> `.opencode/commands/tangle-one.md`
- `todo` -> `.opencode/commands/todo.md`
- `pvox` or `voxforge` -> `.opencode/skills/helmcortex-pvox/SKILL.md`
- `antigravity` -> `.opencode/skills/antigravity-config/SKILL.md`
- `skill-sync` -> `.opencode/commands/skill-sync.md`

Then inspect the matching org file or area only as needed.

## Rules

- Keep the orientation concise
- Load context just in time, not just in case
- Prefer canonical org sources over generated overlays during orientation
- Flag likely 3+ file or control-plane changes early so implementation does not start blind
