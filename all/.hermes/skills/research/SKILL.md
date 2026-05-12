---
name: research
description: Create or open a research scaffold in MetaCortex — routes to Projects/, Evaluations/, or Research/ based on type.
---

*description: Create or open a research scaffold in MetaCortex — routes to Projects/, Evaluations/, or Research/ based on type.*

> **Model:** `gpt-5.4` | **Effort:** `high` | **Delegate:** `claude-sonnet`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# /research — MetaCortex Research Scaffold

Create or open a MetaCortex document. Arguments: $ARGUMENTS

## Three Document Types

| Type | Folder | Use When |
|------|--------|----------|
| `project` | `Projects/` | Something WE BUILD — linked to PromptGolf hole + TODO |
| `evaluation` | `Evaluations/` | External project we are scoping for integration |
| `research` | `Research/` | Landscape doc, synthesis, cross-cutting analysis |

## Usage
- `/research evaluation <project-name>` — external project evaluation (default if type omitted)
- `/research evaluation <project-name> <github-url>` — evaluation with repo metadata
- `/research project <project-name>` — our own project scaffold
- `/research research <topic-name>` — synthesis/landscape doc

## Steps

### 1. Parse Arguments
Extract type (`project` | `evaluation` | `research` — default `evaluation`) and name (kebab-case), optional GitHub URL.

### 2. Determine Target Folder
- `evaluation` → `CORTEX/GoldenAge_Loom/MetaCortex/Evaluations/<name>-evaluation.md`
- `project` → `CORTEX/GoldenAge_Loom/MetaCortex/Projects/<name>.md`
- `research` → `CORTEX/GoldenAge_Loom/MetaCortex/Research/<name>.md`

### 3. Check for Existing Doc
`obsidian read path="<target-path>"` — if it exists, display and stop.

### 4. Fetch Repo Metadata (evaluation + GitHub URL only)
`gh repo view <url> --json name,description,licenseInfo,primaryLanguage,pushedAt,stargazerCount,url`

### 5. Ask Classifying Questions

**For evaluation:** "Dionysus / Hierem / Both?" and "Integration target: NEXUS | CORE | component?"
**For project:** "Which PromptGolf hole does this map to?" and "Which TODO file?"
**For research:** "What is the core question this doc answers?"

### 6. Create Doc

Use `obsidian create` with the appropriate template:

**Evaluation template:**
```markdown
# <Project Name> — Evaluation

*Evaluated: YYYY-MM-DD*
*Status: evaluating*
*Layer: <Dionysus | Hierem | Both>*
*Integration target: <NEXUS | CORE | component>*

## What Is It?
<description>

- **GitHub**: <url>
- **License**: <from gh>
- **Language**: <from gh>
- **Activity**: <last push>

## Core Architecture

## WarMap Alignment
| Axis | Score | Notes |
|------|-------|-------|
| Freedom (Stallman) | /10 | |
| Sovereignty (Terry) | /10 | |
| Privacy (Snowden) | /10 | |
| Purity (Bufo) | /10 | |
| Gnosis (Prometheus) | /10 | |
| Eros (Christos) | /10 | |

## Overlap with Existing Systems
| Feature | Ours | <Project> |
|---------|------|-----------|

## Integration Path

## Decision
- [ ] Approve / Reject / Defer — reason:
```

**Project template:**
```markdown
# <Project Name>

*Created: YYYY-MM-DD*
*Status: active*
*PromptGolf hole: <hole-id>*
*TODO: [[LOGS/TODO/HelmCortex]]*

## What Are We Building?

## Architecture

## Open Questions

## Decisions
```

**Research template:**
```markdown
# <Topic> — Research

*Created: YYYY-MM-DD*
*Status: in-progress*

## Core Question

## Findings

## Sources
```

### 7. Update MetaCortex Index
Edit `CORTEX/GoldenAge_Loom/MetaCortex/README.md`:
- **Evaluation**: insert under correct layer heading in `## Evaluations` section: `- [[Evaluations/<name>-evaluation|<Name>]] — <summary> **WarMap: XX/60**`
- **Project**: insert under `## Projects`: `- [[Projects/<name>|<Name>]] — <one-line summary>`
- **Research**: insert under `## Research`: `- [[Research/<name>|<Name>]] — <one-line summary>`

### 8. Check for Related WebClippings
`obsidian search query="<name>" limit=20` — filter to `LOGS/WebClipper/`. If any match, append `## WebClippings` section with wikilinks.

## Rules
- Names are always kebab-case
- One doc per project — never duplicate
- Always update `MetaCortex/README.md` index
- If relevant to an existing landscape doc in `Research/`, add to its comparison table too

