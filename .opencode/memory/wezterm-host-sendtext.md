# WezTerm Host Send Text

Key WezTerm behavior learned from prior work.

## Host Architecture

- WezTerm is installed as a Flatpak
- Pane commands run on the host via portal integration, not inside the Flatpak sandbox
- `flatpak-spawn --host` is not the right model for this setup
- Guix binaries may need direct host paths such as `~/.guix-extra-profiles/core/core/bin/zsh`

## Echo Suppression Pattern

- Bash echoes the full command line before execution
- `stty -echo && cmd` in one injected line is too late to prevent the echo
- The correct pattern is to inject `stty -echo` first, then inject the real command after a short delay

## Working Lua Pattern

```lua
pane:send_text('stty -echo' .. CR)
wezterm.time.call_after(0.15, function()
  pane:send_text('clear && ' .. host_cmdline('fastfetch') .. CR)
end)
```

Use this when working on WezTerm startup panes and host-side command injection.
