# Antigravity Workflow

Antigravity belongs to DotCortex's `nala.org` layer on this machine.

## Ownership

- Source of truth for install and repo metadata: `~/DotCortex/nala.org`
- Source of truth for Antigravity user config tangles: `~/DotCortex/nala.org`
- Tangled targets:
  - `~/DotCortex/debian/.nala/manifest/packages.ssv`
  - `~/DotCortex/debian/.nala/manifest/repos.ssv`
  - `~/DotCortex/linux/.config/Antigravity/User/settings.json`
  - `~/DotCortex/linux/.config/Antigravity/User/keybindings.json`
  - `~/DotCortex/linux/.local/share/applications/antigravity.desktop`
- Live user config:
  - `~/.config/Antigravity/User/settings.json`
  - `~/.config/Antigravity/User/keybindings.json`
  - `~/.local/share/applications/antigravity.desktop`

## Package Source

- Native package name: `antigravity`
- Third-party apt repo is the Google Antigravity repository documented in `~/HelmCortex/LOGS/WebClipper/Google Antigravity.md`
- DotCortex should manage both the repo entry and package install through `nala.org`

## Current Defaults

- `claudeCode.preferredLocation`: `panel`
- `terminal.integrated.commandsToSkipShell` must include `workbench.action.terminal.sendSequence`
- terminal `Shift+Enter` works by sending `"\u001b\u000d"` with `workbench.action.terminal.sendSequence`
- keep an explicit `-workbench.action.terminal.sendSequence` unbind before the custom `Shift+Enter` binding
- Vim mode enabled
- `vim.useSystemClipboard` enabled
- terminal profiles point at Guix zsh
- VSCode Neovim should use `/home/metsatron/.guix-extra-profiles/core/core/bin/nvim`
- Antigravity launcher should export a PATH that includes `~/.local/bin`, `~/.npm-global/bin`, and Guix core bin paths for extension host CLI discovery

## Important Distinction

- The actual editor in use is Google Antigravity, installed natively
- A separate project called Antigravity Agent exists for managing multiple Google Antigravity accounts
- That account tool is not the editor itself and should not be confused with DotCortex ownership of the editor

## Operating Pattern

1. Edit `nala.org`
2. Run `tangle-one nala.org` or `make tangle`
3. Apply package/repo changes with `loom nala:apply` or the corresponding `nala-*` helpers when relevant
4. Apply config changes with `make safe-stow` or `stow linux`
5. Restart Antigravity if terminal behavior or keybindings do not reload live

## Hotfix Discipline

- If a live edit is made under `~/.config/Antigravity/` or `~/.local/share/applications/`, mirror it back into `nala.org` before ending the task
- Treat direct live edits as temporary repair unless the user explicitly wants a one-off divergence from DotCortex

## Shift+Enter Fix

The earlier `\r`, `Ctrl+V`, and backslash-based attempts were wrong for this app.

What actually works in Antigravity's integrated terminal on Linux with zsh:

- let the terminal keybinding be intercepted before the shell by adding
  `workbench.action.terminal.sendSequence` to
  `terminal.integrated.commandsToSkipShell`
- send `ESC + Enter` as `"\u001b\u000d"`

This gives multiline continuation in the integrated terminal after a full app
restart.
