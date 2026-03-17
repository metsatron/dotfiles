# PVOX Workflow

Stateless reference for speaking through HelmCortex VoxForge.

## Canonical Paths

- VoxForge root: `~/HelmCortex/FORGE/VoxForge`
- Runtime binary: `~/HelmCortex/FORGE/VoxForge/bin/pvox`
- Literate config: `~/HelmCortex/FORGE/VoxForge/docs/pvox.md`
- Pied Flatpak models: `~/.var/app/com.mikeasoft.pied/data/pied/models`
- Speech Dispatcher Piper config: `~/.config/speech-dispatcher/modules/piper.conf`

## Voice Conventions

- `Default` -> `en_US-amy-medium.onnx`
- `Claude` -> `en_US-amy-medium.onnx`
- `ClaudeMX` -> `es_MX-claude-high.onnx`

Use Amy Medium for full answers.
Use `ClaudeMX` for short attention cues and brief spoken summaries such as `Tudo pronto, meu comandante!`.

## Preferred Commands

### Long-form speech

```bash
printf '%s' "your text here" | ~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin
```

### Streaming speech

```bash
printf '%s' "your text here" | PVOX_PLAYER_RAW=aplay ~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin --stream
```

### Attention cue

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox say ClaudeMX --stream "Tudo pronto, meu comandante!"
```

### Short spoken summary

```bash
printf '%s' "resumo curto aqui" | PVOX_PLAYER_RAW=aplay ~/HelmCortex/FORGE/VoxForge/bin/pvox say ClaudeMX --stdin --stream
```

### Current Speech Dispatcher voice

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox sd-show
```

### Set Speech Dispatcher default

```bash
~/HelmCortex/FORGE/VoxForge/bin/pvox sd-default Claude --yes
```

## Playback Notes

- `pvox say ...` is reliable file playback
- `pvox say ... --stream` is raw playback and should prefer `PVOX_PLAYER_RAW=aplay` on this machine
- `pclip default` is for user-driven selected-text playback and is bound to `Meta+V`
- Runtime truth lives in the JSON block inside `docs/pvox.md`, not stale prose or old scripts
