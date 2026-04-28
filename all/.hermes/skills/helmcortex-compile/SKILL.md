---
name: helmcortex-compile
description: Compile FORGE templates into CLAUDE.md, AGENTS.md, skills, hooks, and per-agent context files across all scopes.
---

*description: Compile FORGE templates into CLAUDE.md, AGENTS.md, skills, hooks, and per-agent context files across all scopes.*

Run the compile pipeline. Optionally scope to a workspace or specific type.

```bash
helmcortex-compile [--type agents|skills|commands|context|hooks|all] [--scope HelmCortex|FORGE|bridge|PalmCortex] [--dry-run]
```

## Common invocations

```bash
helmcortex-compile                          # compile everything
helmcortex-compile --dry-run                # preview without writing
helmcortex-compile --type agents            # AGENTS.md/CLAUDE.md only
helmcortex-compile --type context           # MEMORY/SOUL/USER outputs only
helmcortex-compile --scope FORGE            # FORGE scope, all types
helmcortex-compile --type skills --dry-run  # preview skill output
```

After any harness edit in `FORGE/harness/{workspace}/`, run compile to propagate.
Context templates are `MEMORYS.md`, `SOULS.md`, and `USERS.md`; they emit `MEMORY.md`, `SOUL.md`, and `USER.md` into each scoped dot-agent directory.
After compile, run `git diff` to review what changed before committing.

