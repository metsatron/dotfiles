---
name: helmcortex-forge
description: FORGE scripts — how to run them, what they do, gotchas. Load for any task involving script execution, digest pipelines, or new script creation.
---

*description: FORGE scripts — how to run them, what they do, gotchas. Load for any task involving script execution, digest pipelines, or new script creation.*

> **Model:** `gpt-5.4-mini` | **Effort:** `low` | **Delegate:** `mini`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# HelmCortex FORGE Scripts

All scripts live in `FORGE/bin/` and are PATH-blessed via GNU Stow from DotCortex. Run by name from any directory.

## Core Scripts

### helmcortex-sync
```bash
helmcortex-sync
```
Backs up and mirrors HelmCortex across drives. One-way sync to 3 drives minimum. Reports changed file counts and errors. Run after any significant session.

### helmcortex-readme-indexer
```bash
helmcortex-readme-indexer
```
Generates README.md index files across all HelmCortex directories. Reports which READMEs were updated or created.

### chatgpt-md-pipeline
```bash
chatgpt-md-pipeline
```
Deblobbing pipeline for ChatGPT markdown exports. Processes raw `.md` files from ChatGPT ZIP exports into clean, sliced, indexed format under `LOGS/ChatGPT/`.

### chatgpt-memory-pipeline
```bash
chatgpt-memory-pipeline
```
Processes LumenAstra memory exports. Standardizes and merges memory files.

### pvox
```bash
pvox say Claude --stream "text"
pvox stream --rule ChatGPT ~/HelmCortex/LOGS/ChatGPT/.SLICED/session.md
pvox streamdir --rule Claude ~/HelmCortex/LOGS/Claude/EXPORT/
pvox render --rule Grok file.md out.wav
pvox list        # show all configured voices
pvox agents      # show all agent assignments
```
Voice engine for HelmCortex. See `@helmcortex-pvox` skill for full usage.

### claude-code-md-pipeline
```bash
claude-code-md-pipeline
```
Processes Claude Code session exports into clean markdown for LOGS/Claude/.

### telegram-process-exports
```bash
telegram-process-exports
```
Converts Telegram JSON exports to markdown format for LOGS/Telegram/.

### gab_process_hars.sh
```bash
gab_process_hars.sh
```
Extracts Gab.AI conversations from HAR files captured via browser dev tools.

### perplexity-md-pipeline
```bash
perplexity-md-pipeline
```
Processes Perplexity conversation exports (Auryn sessions) into LOGS/Perplexity/.

### grok-md-pipeline
```bash
grok-md-pipeline
```
Processes Grok conversation exports (Makína Kènè sessions) into LOGS/Grok/.

### hermes-md-pipeline
```bash
hermes-md-pipeline                        # process new/updated sessions
hermes-md-pipeline --list                 # list all sessions
hermes-md-pipeline --dry-run -v           # preview output paths
hermes-md-pipeline SESSION_ID            # process specific session
hermes-md-pipeline --force               # overwrite existing files
hermes-md-pipeline --roll-only           # rebuild .ROLLED digests only
```
Converts Hermes Agent SQLite sessions (`~/.hermes/state.db`) to Obsidian Markdown under `LOGS/Hermes/`. Outputs `.MASTER/` (one file per session), `CHUNKED/` (multi-part for long sessions), and `.ROLLED/` (weekly digests). Scans `~/mnt/*/\.hermes/state.db` for multi-machine runs.

## FORGE Doctrine

- FORGE contains no final knowledge — it is process, living code and compost.
- Scripts are mycelium: they transform raw LOGS material into structured ROOTS/CORTEX content.
- New scripts go in `FORGE/bin/`. Documentation goes in sibling `FORGE/docs/` or `FORGE/<subproject>/docs/` — never inside `bin/`.
- When creating a new script: make executable (`chmod +x`), add shebang, document in relevant README.

## Gotchas

- Scripts expecting ChatGPT exports require the standard ZIP structure from OpenAI export — do not rename the root folder before processing.
- `chatgpt-md-pipeline` and `chatgpt-memory-pipeline` are separate pipelines for different output types — run both for full processing.
- `pvox` requires Pied (Flatpak) for voice model downloads; playback uses paplay→aplay→ffplay→pw-play cascade.
- For indexers that move files and rewrite backlinks, preserve both original and normalized paths in state. First runs need the old paths to detect pre-normalization backlinks and apply rewrites correctly.
- For YouTube clip recovery, parse video IDs from `youtube.com/redirect?...&v=` links as well as standard watch, shorts, embed, live, and `youtu.be` URLs. Only fall back to title matching when the title is unique in local history or the creator slug disambiguates it.
- For repo-wide backlink or significance scans, prefilter candidate files with `rg -l -F --no-ignore` before opening files in Python. Hidden/generated trees can otherwise hide real matches and make the scan cost explode.
- Leave URL-less summary artifacts unresolved and logged unless a safe local match exists. Do not guess a canonical target from prose alone.
- **MD pipeline tool names differ per framework** — before writing any tool-name comparison in a pipeline, grep a CHUNKED output to confirm the real name. Claude Code uses `Read`; OpenCode uses `read` (lowercase) with `filePath`; Hermes uses `read_file` with `path`. Full table in `FORGE/docs/md-pipeline-conventions.md`.

