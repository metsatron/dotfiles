---
name: chatgpt-pipeline
description: Run both ChatGPT pipelines in sequence — MD export deblob and memory pipeline.
---

*description: Run both ChatGPT pipelines in sequence — MD export deblob and memory pipeline.*

> **Model:** `gpt-5.4-mini` | **Effort:** `low` | **Delegate:** `mini`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# /chatgpt-pipeline

Run both ChatGPT pipelines in sequence. Report pipeline steps completed and any errors.

```bash
chatgpt-md-pipeline && chatgpt-memory-pipeline
```

