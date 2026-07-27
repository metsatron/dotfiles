---
name: redstone-9x-refresh
description: Safely refresh DotCortex-managed menus, launchers, wrappers, shell files, and Desktop Scheme config in an already-running Redstone 9X IceWM sanctuary. Use when Redstone changes were tangled or stowed but are not visible, when a live room needs reprojection without relaunching Xephyr, or when deciding whether a Redstone change requires refresh versus full relaunch.
---

# Refresh a Running Redstone 9X Room

Use the canonical refresh lane after changing DotCortex-managed Redstone files while
the IceWM room is already running. Do not reproduce the old Claude "hot projection"
pattern with direct `cp`, guest edits, or hand-run `icewm --restart` commands.

## Workflow

1. Edit only the owning root Org source.
2. Tangle only that source with `tangle-one <source>.org`.
3. Check the live projection:

   ```bash
   cd ~/DotCortex
   loom redstone:check
   ```

4. Refresh through Loom:

   ```bash
   loom redstone:refresh
   ```

5. Run `loom redstone:check` again. Report any remaining stale or missing files.

`redstone:refresh` calls `sanctuary-redstone-9x-refresh`. The helper refuses to
operate unless it finds both Xephyr `:93` and the IceWM process whose live `DISPLAY`
is `:93`. It projects the lightweight guest-home layer, removes retired managed
launchers, reapplies the active scheme in file-only mode, regenerates
`terminal-theme.zsh`, and reloads IceWM in the existing room. PCManFM watches the
desktop launcher directory itself; this build has no supported `--reconfigure` flag.

## Refresh or Relaunch

Refresh these live:

- IceWM menu, toolbar, preferences, keys, winoptions, and startup file content
- desktop `.desktop` launchers
- Redstone terminal, DOS, Wine, Rofi, and application wrappers
- shell identity files and the default terminal theme module
- Desktop Scheme declarations, GTK templates, and Qt palettes

Require a full sanctuary relaunch for:

- Guix profile/package changes or a rebuilt profile generation
- session environment or PATH changes
- Distrobox/Podman mounts, container hooks, or container-layer changes
- Xephyr geometry/options
- adding/removing startup processes or anything that must inherit a new environment

If the helper says the room is not running, do not launch it merely to test the
refresh. Report that state or relaunch only when the user asked for a launch.

## `redstone:refresh` does NOT reload icons — it does not restart pcmanfm

The refresh reloads IceWM. `pcmanfm --desktop` **survives it with the same PID**, holding every icon it resolved at startup, so an icon-tree change is invisible no matter how many times you refresh. Do not kill it — nothing is guaranteed to respawn it and the desktop goes with it.

The lever is XSETTINGS: GTK rebuilds its icon cache when the theme *name* changes. Flip it away and back, HUP each time, and restore the file byte-for-byte:

```bash
C=~/.local/share/dotcortex/guests/sanctuary-redstone-9x/home/.config/xsettingsd/xsettingsd.conf
cp "$C" /tmp/xsettingsd.orig
sed -i 's|^Net/IconThemeName ".*"|Net/IconThemeName "Chicago95"|' "$C"; pkill -HUP -x xsettingsd; sleep 3
cp /tmp/xsettingsd.orig "$C"; pkill -HUP -x xsettingsd
```

Expect a visible flash of the intermediate theme. Verify with `diff` that the config is back to its original.

**Order matters, and it is the cheap mistake.** Write the files first, THEN refresh. A refresh that ran before the change landed proves nothing, and the resulting "it didn't work" sends you hunting for a cache bug that isn't there — check `ps -eo pid,lstart` for the consumer against the file's `stat` mtime before theorising.

## Taskbar widgets are invisible to `xwd -root`

`xwd -root` does not capture the IceWM taskbar's child windows on `:93`. Crop the taskbar band and you get pure wallpaper, which reads exactly like "the widget isn't rendering" — it is, you just cannot see it. Even `xwd -id <TaskBar>` misses them, because the Start button, pager and tray are each their own X window.

Use `xwininfo -root -tree` as the primary evidence (it lists `Workspaces`, `TaskBarMenu`, `SystemTray` with geometry and children), and `xwd -id <the specific child>` when you need pixels. Never conclude a taskbar widget is missing from a root capture.

## The guest has no `/usr/bin/env` — shebangs must be `#!/bin/bash`

Any new `redstone-9x-*` wrapper must use `#!/bin/bash`. The sanctuary guest is a Guix-populated container: `/bin/bash` is a store symlink, but `/usr/bin/env` was never created and does not exist. A `#!/usr/bin/env bash` script runs perfectly on the host and fails at `exec` time in the room with `ENOENT`.

The trap is the error text. IceWM reports it as:

```
IceWM: Warning: Failed to execute /home/metsatron/.local/bin/redstone-9x-<tool>: No such file or directory
```

which names *the launcher*, not the interpreter — so it reads as a broken symlink or an unstowed file, and sends you auditing `ls -l` on a symlink that is perfectly correct. Check the shebang first: `head -1` the tangled script and compare it against a sibling that works. Every existing wrapper already uses `#!/bin/bash`.

Confirm interpreter presence in-guest rather than on the host, since the host has both:

```bash
sanctuary-exec sanctuary-redstone-9x sh -c 'ls -l /usr/bin/env /bin/bash'
```

## Safety

- Never edit files under `linux/` directly; they are tangled output.
- Never write into the guest with bare `podman exec`; it runs as container root.
- Never use blanket `pkill` in a shared sanctuary PID namespace.
- Never use a visible `:93` application launch as verification. The refresh itself
  may reload the existing WM, but verification stays file/process based.
- Use `sanctuary-redstone-9x-refresh --no-reload` only when the user explicitly
  wants projection without a WM reload.

## Canonical Owners

- Helper: `sanctuary-redstone-9x-refresh.org`
- Loom verbs: `loom.org`
- This skill: `agents-skills-dotcortex.org`
