Session reflection — analyse what happened, persist learnings, surface improvements.

Spawn a subagent (model: claude-haiku-4-5) to analyse this session. The subagent should:

1. Read the full conversation context available to it
2. Read `.claude/MEMORY.md` for current state
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

After receiving the subagent response, act on it:

- **NEW_FACTS**: Append to `## Session Facts` section of `.claude/MEMORY.md`. If file exceeds 2000 chars, trim oldest entries from Session Facts to fit.
- **PREFERENCE_UPDATES**: Append to `## User Model` section of `.claude/MEMORY.md`. If User Model section exceeds 1500 chars, trim oldest entries to fit.
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
