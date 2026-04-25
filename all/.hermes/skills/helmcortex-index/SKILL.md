---
name: helmcortex-index
description: Run helmcortex-readme-indexer and report updated READMEs.
---

*description: Run helmcortex-readme-indexer and report updated READMEs.*

> **Model:** `gpt-5.4-mini` | **Effort:** `low` | **Delegate:** `mini`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# /helmcortex-index

Use the indexer deliberately.

- For local README/docs work, prefer a narrow run first:
  `helmcortex-readme-indexer --no-commit <path ...>`
- Re-read the generated files after the run. Do not assume manual README edits survived.
- If a module README needs a durable intro, write it as a leading blockquote
  hero/epigraph immediately after the H1. The indexer preserves that block; plain
  intro paragraphs are treated as normal body text.
- If the content lives in a ritual-injected README section, edit the sibling
  `docs/ritual.md` source file, then rerun the indexer.
- Use the bare full-repo command only for intentional broad regeneration.

Report errors and which READMEs/docs were updated.

```bash
helmcortex-readme-indexer --no-commit FORGE README.md docs/ritual.md
```

