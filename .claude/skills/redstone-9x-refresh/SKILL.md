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
