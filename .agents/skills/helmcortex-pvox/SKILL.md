---
name: helmcortex-pvox
description: Speak through VoxForge pvox with Flatpak Pied models.
---

# HelmCortex PVOX Operations

Use this skill when the task involves speaking text through VoxForge, checking Piper voices, or using `pvox` with Flatpak-managed Pied models.

## Use This Skill For

- Speaking assistant output aloud through `pvox`
- Checking which voice or model is active
- Streaming transcript files or directories
- Setting or inspecting the Speech Dispatcher Piper default
- Verifying Flatpak-managed Pied model availability

## Canonical Runtime Paths

- VoxForge root: `~/HelmCortex/FORGE/VoxForge`
- Runtime binary: `~/HelmCortex/FORGE/VoxForge/bin/pvox`
- Canonical config source: `~/HelmCortex/FORGE/VoxForge/docs/pvox.md`
- Flatpak Pied models: `~/.var/app/com.mikeasoft.pied/data/pied/models`
- Speech Dispatcher Piper config: `~/.config/speech-dispatcher/modules/piper.conf`

## Voice Defaults

- Default voice: `en_US-amy-medium.onnx`
- Claude voice: `en_US-amy-medium.onnx` (Amy Medium)
- Attention cue voice: `ClaudeMX` -> `es_MX-claude-high.onnx`
- `pclip default` follows the current Speech Dispatcher Piper default

## Speaking Convention

- Full answer or selected prose -> `Claude` / Amy Medium
- Short completion, attention cue, or brief spoken summary -> `ClaudeMX`
- Default cue text when useful: `Tudo pronto, meu comandante!`

## Preferred Speaking Path

Default to direct `pvox` playback for interactive speech:

```bash
printf '%s' "your text here" | ~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin
```

Low-latency streaming:

```bash
printf '%s' "your text here" | PVOX_PLAYER_RAW=aplay ~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin --stream
```

Short attention cues use the Spanish Claude model:

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox say ClaudeMX --stream "Tudo pronto, meu comandante!"
```

Brief spoken summaries also use `ClaudeMX`:

```bash
printf '%s' "resumo curto aqui" | PVOX_PLAYER_RAW=aplay ~/HelmCortex/FORGE/VoxForge/bin/pvox say ClaudeMX --stdin --stream
```

Speech Dispatcher path (useful for `pclip default` and system voice routing):

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox spd Claude --stdin
```

## Core Commands

```bash
pvox list                          # list all configured voices
pvox agents                        # show agent voice assignments
pvox sd-show                       # show current Speech Dispatcher voice
pvox speakers Claude               # show Claude voice details
pvox speakers ClaudeMX             # show ClaudeMX voice details
pvox say Claude --stream "text"    # speak with Amy
pvox say ClaudeMX --stream "text"  # speak with Spanish Claude
pvox spd Claude "text"             # speak via Speech Dispatcher
pvox stream --rule Claude file.md  # stream a transcript file
pvox streamdir --rule Claude dir/  # stream a directory of transcripts
pvox sd-default Claude --yes       # set SD default to Claude/Amy
```

## Safety Checks

Before speaking, verify:

1. `~/HelmCortex/FORGE/VoxForge/bin/pvox` exists and is executable
2. The Flatpak Pied models directory exists: `~/.var/app/com.mikeasoft.pied/data/pied/models`
3. The requested model file exists inside that directory
4. If using `pclip default`, the Speech Dispatcher default is set to the intended model

## Operational Notes

- Runtime truth comes from the JSON block in `docs/pvox.md`, not stale prose examples
- VoxForge expects Flatpak-managed Pied assets, not Snap or AppImage model paths
- Direct `pvox say` is the most reliable path for speaking assistant output
- Raw `--stream` playback should prefer `aplay` first on this machine, with `ffplay` fallback
- `Meta+V` is bound to `pclip default` for user-driven selected-text playback
- Player env vars: `PVOX_PLAYER=paplay` (WAV), `PVOX_PLAYER_RAW=aplay` (raw streaming)
