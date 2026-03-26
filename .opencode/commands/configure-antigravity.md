# configure-antigravity - Antigravity Through DotCortex

Use this when the user wants Antigravity configured on this machine.

## Load First

1. `.opencode/memory/antigravity.md`
2. `.opencode/skills/antigravity-config/SKILL.md`

## Workflow

1. Confirm whether the task is about the editor itself or the separate multi-account helper tool
2. Read the owning Antigravity blocks in `nala.org`
3. Make changes in `nala.org`
4. Run `tangle-one nala.org` or `make tangle`
5. Apply package/repo changes with the Nala flow when needed
6. Apply config changes with `make preview-stow`, `make safe-stow`, or the relevant Loom stow verb when needed
7. Verify the live config in `~/.config/Antigravity/User/`
8. Tell the user whether a reload or full restart is needed

## Defaults To Preserve

- `claudeCode.preferredLocation`: `panel`
- terminal `Shift+Enter` newline behavior
- Vim bindings enabled
- Guix zsh terminal profiles

## Rules

- prefer DotCortex-managed edits over direct home-directory patching
- keep Antigravity ownership in `nala.org`
- do not add Flatpak Antigravity integration unless the user explicitly reopens that path
- do not confuse the editor with the separate multi-account helper tool
- keep final reporting concrete and path-specific
- include fresh verification evidence instead of assuming the live config matches the tangle
