---
name: antigravity-config
description: Manage Google Antigravity from DotCortex, including apt repo/package ownership in `nala.org` and editor config tangles.
---

# Antigravity Config via DotCortex

Use this skill when the user wants to configure Antigravity on this machine.

## Trigger Conditions

- user asks to configure Antigravity
- user mentions Antigravity install, apt repo, `Shift+Enter`, shell defaults, Vim mode, keybindings, or Antigravity settings
- user wants Antigravity managed from DotCortex rather than ad hoc edits in `~/.config`

## Source Of Truth

- Edit `~/DotCortex/nala.org`
- Do not edit `~/DotCortex/linux/.config/Antigravity/User/*.json` directly unless repairing a broken tangle during the current task
- Do not edit `~/DotCortex/debian/.nala/manifest/*.ssv` directly unless repairing a broken tangle during the current task
- Do not edit `~/.config/Antigravity/User/*.json` directly unless the user explicitly asks for a one-off hotfix outside DotCortex

## Current Owned Targets

- `debian/.nala/manifest/packages.ssv`
- `debian/.nala/manifest/repos.ssv`
- `linux/.config/Antigravity/User/settings.json`
- `linux/.config/Antigravity/User/keybindings.json`
- `linux/.local/share/applications/antigravity.desktop`

## Known Defaults

- package name: `antigravity`
- Google Antigravity apt repo is managed from `nala.org`
- `claudeCode.preferredLocation`: `panel`
- `terminal.integrated.commandsToSkipShell` must include `workbench.action.terminal.sendSequence`
- terminal `Shift+Enter` -> explicit unbind plus `workbench.action.terminal.sendSequence` with `"\u001b\u000d"`
- `vscode-neovim.neovimExecutablePaths.linux` should point to `/home/metsatron/.guix-extra-profiles/core/core/bin/nvim`
- do not point `vscode-neovim.neovimInitVimPaths.linux` at the `nvim` binary
- Vim mode enabled
- system clipboard enabled for Vim mode
- terminal profiles prefer Guix zsh

## Procedure

1. Read the Antigravity sections in `nala.org`
2. Update the owning source blocks there
3. Run `tangle-one nala.org` or `make tangle`
4. Apply package/repo changes with `loom nala:apply` or the `nala-*` helpers if needed
5. Apply config changes with `make preview-stow`, `make safe-stow`, or the relevant Loom stow verb as appropriate
6. Re-read the generated files if needed to confirm exact output
7. Tell the user whether Antigravity likely needs reload or full restart
8. If you hotfix the live Antigravity files first, port the same change back into `nala.org` before finishing

## Guardrails

- Do not treat Antigravity as a Flatpak target unless the user explicitly reopens that migration
- Do not confuse Google Antigravity with the separate Antigravity Agent account-management tool
- Keep unrelated package-manager churn out of Antigravity-only work
- Do not claim the live config is correct without fresh verification evidence

## Shift+Enter Pattern

For Antigravity's integrated terminal on Linux with zsh, the known-good fix is:

```json
{
  "terminal.integrated.commandsToSkipShell": [
    "workbench.action.terminal.sendSequence"
  ]
}
```

```json
[
  {
    "key": "shift+enter",
    "command": "-workbench.action.terminal.sendSequence",
    "when": "terminalFocus"
  },
  {
    "key": "shift+enter",
    "command": "workbench.action.terminal.sendSequence",
    "args": { "text": "\u001b\u000d" },
    "when": "terminalFocus"
  }
]
```

Why it works:

- Antigravity must intercept the keybinding before zsh consumes it
- zsh then receives `ESC + Enter`, which produces multiline continuation in the
  integrated terminal

## Useful Paths

- `~/DotCortex/nala.org`
- `~/DotCortex/debian/.nala/manifest/packages.ssv`
- `~/DotCortex/debian/.nala/manifest/repos.ssv`
- `~/DotCortex/linux/.config/Antigravity/User/settings.json`
- `~/DotCortex/linux/.config/Antigravity/User/keybindings.json`
- `~/DotCortex/linux/.local/share/applications/antigravity.desktop`
- `~/.config/Antigravity/User/settings.json`
- `~/.config/Antigravity/User/keybindings.json`
- `~/.local/share/applications/antigravity.desktop`
- `/usr/bin/antigravity`
