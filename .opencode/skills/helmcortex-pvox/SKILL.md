---
name: helmcortex-pvox
description: Use HelmCortex VoxForge `pvox` to speak text, stream transcripts, inspect voice mappings, and work against Flatpak-managed Pied models.
---

# HelmCortex PVOX Operations for OpenCode

Use this skill when the task is about speaking text through VoxForge, checking Piper voices, or using `pvox` with Pied Flatpak-managed models.

## Use This Skill For

- speaking assistant output aloud through `pvox`
- checking which voice or model is active
- streaming transcript files or directories
- setting or inspecting the Speech Dispatcher Piper default
- verifying Flatpak-managed Pied model availability

## Canonical Runtime Paths

- VoxForge root: `~/HelmCortex/FORGE/VoxForge`
- Runtime binary: `~/HelmCortex/FORGE/VoxForge/bin/pvox`
- Canonical config source: `~/HelmCortex/FORGE/VoxForge/docs/pvox.md`
- Flatpak Pied models: `~/.var/app/com.mikeasoft.pied/data/pied/models`
- Speech Dispatcher Piper config: `~/.config/speech-dispatcher/modules/piper.conf`

## Voice Defaults

- Default voice: `en_US-amy-medium.onnx`
- Claude voice: `en_US-amy-medium.onnx`
- Attention cue voice: `ClaudeMX` -> `es_MX-claude-high.onnx`
- `pclip default` should follow the current Speech Dispatcher Piper default

## Speaking Convention

- Full answer or selected prose -> `Claude` / Amy Medium
- Short completion, attention cue, or brief spoken summary -> `ClaudeMX`
- Default cue text when useful: `Tudo pronto, meu comandante!`

## Preferred Speaking Path

Default to direct `pvox` playback for interactive speech:

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin
```

Low-latency streaming is also available:

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin --stream
```

Short attention cues can use the Spanish Claude model:

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox say ClaudeMX --stream "Tudo pronto, meu comandante!"
```

Brief spoken summaries should also use `ClaudeMX` rather than Amy:

```bash
printf '%s' "resumo curto aqui" | PVOX_PLAYER_RAW=aplay ~/HelmCortex/FORGE/VoxForge/bin/pvox say ClaudeMX --stdin --stream
```

Speech Dispatcher remains useful for `pclip default` and system voice routing:

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox spd Claude --stdin
```

## Core Commands

```bash
pvox list
pvox agents
pvox sd-show
pvox speakers Claude
pvox speakers ClaudeMX
pvox say Claude --stream "Hello from Amy."
pvox say ClaudeMX --stream "Tudo pronto, meu comandante!"
pvox spd Claude "Hello from Amy via Speech Dispatcher."
pvox stream --rule Claude ~/HelmCortex/LOGS/Claude/example.md
pvox streamdir --rule Claude ~/HelmCortex/LOGS/Claude/
```

## Safety Checks

Before speaking, verify:

1. `~/HelmCortex/FORGE/VoxForge/bin/pvox` exists
2. `models_dir` in `docs/pvox.md` exists
3. the requested model file exists inside the Flatpak Pied models directory
4. if using `pclip default`, the Speech Dispatcher default is set to the intended model

## Useful Patterns

### Speak current response via stdin

```bash
printf '%s' "your text here" | ~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin
```

### Speak current response via raw stream

```bash
printf '%s' "your text here" | PVOX_PLAYER_RAW=aplay ~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin --stream
```

### Check current Speech Dispatcher voice

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox sd-show
```

### Set Speech Dispatcher default to Claude/Amy

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox sd-default Claude --yes
```

### Speak selected clipboard text through the current default

```bash
/home/metsatron/HelmCortex/FORGE/VoxForge/bin/pclip default
```

## Operational Notes

- Runtime truth comes from the JSON block in `docs/pvox.md`, not stale prose examples
- VoxForge now expects Flatpak-managed Pied assets, not Snap or AppImage model paths
- Direct `pvox say` is currently the most reliable path for speaking assistant output in this environment
- Raw `--stream` playback should prefer `aplay` first on this machine, with `ffplay` fallback
- If `Meta+V` is bound to `pclip default`, selecting assistant output and invoking the shortcut should read it aloud with the current default voice
