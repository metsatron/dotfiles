Session reflection — analyse what happened, persist learnings, surface improvements.

Spawn a subagent (model: claude-haiku-4-5) to analyse this session. The subagent should:

1. Read the full conversation context available to it
2. Read `.claude/MEMORY.md` for current state. Note whether it is a **harness projection** (its header names a HelmCortex `MEMORYS.md` source of truth and it carries `<!-- BEGIN LOCAL AGENT NOTES -->` markers) or a **legacy standalone file** — this decides where durable memory is written below.
3. Return a JSON object with these fields:

```json
{
  "NEW_FACTS": ["fact1", "fact2"],
  "PREFERENCE_UPDATES": ["pref1", "pref2"],
  "SKILL_CANDIDATE": null or {"name": "...", "description": "...", "content": "..."},
  "CLAUDE_MD_PROPOSAL": null or "proposed amendment text",
  "QUALITY_SCORE": 1-10
}
```

**NEW_FACTS**: Stable facts learned this session (file paths, gotchas, patterns, tool behaviours). Not session-specific state.

**PREFERENCE_UPDATES**: Inferred user preferences (communication style, workflow habits, tool choices). Only things confirmed by repeated behaviour or explicit statements.

**SKILL_CANDIDATE**: Non-null only if a novel multi-step solution was discovered (>3 tool calls), a new gotcha was found not in dotcortex-gotchas, or a reusable workflow emerged.

**CLAUDE_MD_PROPOSAL**: Non-null only if a Critical Rule or Behavioural Constraint should change based on session evidence. Must be specific (exact line to add/modify).

**QUALITY_SCORE**: 1-10 self-assessment of session quality. 10 = no wasted tool calls, no wrong approaches, no unnecessary output.

After receiving the subagent response, act on it. **Durable memory is written to the source of truth, never to a read-only projection:**

- If `.claude/MEMORY.md` is a **harness projection**: write durable memory into the HelmCortex harness source `~/HelmCortex/FORGE/harness/<scope>/MEMORYS.md` (scope = the workspace basename lowercased, e.g. DotCortex → `dotcortex`) — append **NEW_FACTS** under `## Durable Facts` and **PREFERENCE_UPDATES** under `## User Model`. Then regenerate the projection with `helmcortex-compile --scope <scope> --type context --no-helmstow --no-shims` and commit `MEMORYS.md` by surgical pathspec (HelmCortex is a shared multi-writer repo). Keep the projection lean (~2 KB); distill the harness file when it grows — git history preserves every pre-distill state. Never edit the projection directly.
- If `.claude/MEMORY.md` is a **legacy standalone file**: append **NEW_FACTS** to its `## Session Facts` (trim to keep the file ≤ 2000 chars) and **PREFERENCE_UPDATES** to its `## User Model` (≤ 1500 chars), in the file itself.
- **SKILL_CANDIDATE**: If non-null, show the draft skill content and ask for confirmation before creating it in `.claude/skills/`.
- **CLAUDE_MD_PROPOSAL**: If non-null AND QUALITY_SCORE < 7, show the proposed amendment as a diff. Only write to CLAUDE.md on explicit user approval.

### Obsidian Vault Promotion

For durable discoveries worth promoting beyond session memory, write them to the HelmCortex vault. Resolve vault root at write time:

```bash
HOST=$(hostname)
if [ "$HOST" = "ThinkPad-T480s" ] || [ "$HOST" = "t480s" ]; then
  VAULT="$HOME/mnt/x230/HelmCortex"
else
  VAULT="$HOME/HelmCortex"
fi
```

Vault-relative paths (identical on both machines):
- Durable DotCortex discoveries → `LOGS/TODO/DotCortex.md`
- TODOs discovered during session → appropriate `LOGS/TODO/<project>.md`
- Machine-specific findings → `LOGS/TODO/Machines/<hostname>.md`

Append as a timestamped section. Do not overwrite existing content.

Report: what was persisted, what was promoted to vault, what needs approval (if anything). One paragraph max.
