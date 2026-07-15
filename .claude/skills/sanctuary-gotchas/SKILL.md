---
name: sanctuary-gotchas
description: Sanctuary and XFCE gotchas — Xephyr ghost InputOnly window, XFCE screenshot ghost, Flatpak PulseAudio audio dead, xfconf symlink DotCortex, setxkbmap XkbVariant xfsettingsd, host X utilities Guix container PATH, wallpaper xfdesktop
---

# Sanctuary Gotchas

Covers XFCE, Xephyr, Flatpak, X11, and Distrobox sanctuary issues.

## `podman exec` enters as ROOT and poisons the guest home — use `distrobox enter` (sealed 2026-07-14)

`podman exec <sanctuary> …` runs as **container-root**. Anything it writes into the shared guest home lands root-owned, and the desktop user (`metsatron`, uid 1000) can then neither read nor write it. `distrobox enter <sanctuary> -- …` runs as **metsatron** — the user the desktop actually runs as.

This is not theoretical: verifying the Ports menu with `podman exec` created `~/.cache/dotcortex/` root-owned, IceWM could no longer read its own cache, and the menu reported **"Ports unavailable — RetroPie tree not mounted"** while the tree was mounted and fully readable. A cache fault was surfaced to the user as a mount fault, and sent everyone hunting the wrong bug.

- Writing anything into the guest home: **always `distrobox enter`**. `podman exec` is for read-only inspection only.
- After any container work, check your footprint: `find ~/.local/share/dotcortex/guests/<name>/home -not -user metsatron` must return nothing.
- Corollary for tool design: a cache failure must never change what the user sees. If the data source is readable, serve the real content — cached or not. Reserve "unavailable" for the source genuinely being absent, and never write a placeholder INTO a cache (a bad run then poisons every later good one).

## A running container never picks up host mounts made after it started (sealed 2026-07-14)

Podman establishes bind mounts **when the container starts**. If the mount source is behind an **autofs** automount (e.g. an NFS tree under `~/mnt/`), and the container starts while that automount is not live, it captures an **empty** bind for the entire life of that run. Nested autofs mounts do **not** propagate into a container's mount namespace — `/home/metsatron/mnt` is simply empty inside the guest.

- `podman start` on an **already-running** container is a **no-op**, so a stale empty bind survives every subsequent launch. It works only by luck — when the container happened to start after the automount was triggered.
- **The remedy is a RESTART, never a recreation.** Trigger the automount host-side first (`stat -L` the path), then stop/start the container. `sanctuary-retropie-bind-ensure` does this, and also recovers a container wedged in `Stopping` (bounded stop → escalate to `podman kill` → confirm `Exited` → start).
- Never tell the user to recreate a sanctuary to fix a stale mount. Recreation is heavyweight, human-gated, and touches the only thing holding their data.

## Distrobox bakes its helper paths into the container at CREATE time (sealed 2026-07-14)

`distrobox create` records the **host paths** of `distrobox-init`, `distrobox-export` and `distrobox-host-exec` as bind mounts inside the container. Move or remove distrobox and every existing container that referenced the old path becomes **unstartable** — `crun: cannot stat …/distrobox-export`.

Removing distrobox from the Guix core manifest (it was destroying rootless podman storage) orphaned three sanctuaries this way. Recreation is the only fix; the bind sources are immutable container config.

It also changed the *contract*: system distrobox (1.8.x) requires ~30 base commands inside the container and shells out to a **package manager** when any are missing — and a Guix image has none. `sanctuary-base` must therefore satisfy that dependency list natively (see `guix.org`), and pre-seed `/etc/passwd.done` so `distrobox-init` skips its root-password step (Guix's `passwd` is PAM-linked, the image has no PAM service, and the `chpasswd -e` fallback runs unprivileged and cannot open `/etc/passwd`).

## RetroArch ships an `.info` stub for every core that ever existed — only the `.so` is real (sealed 2026-07-14)

`ls lib/libretro/ | grep prboom` "finds" a core that is not installed: `prboom_libretro.info` is metadata, present for hundreds of cores that are absent. **Only `*_libretro.so` proves a core exists.** This produced a false positive that nearly closed a bug that was still open.

## Flatpak audio dead after PulseAudio restart

Killing PulseAudio (`pulseaudio -k`) destroys `/run/flatpak/pulse/` which `flatpak-session-helper` created at login. The helper does not recreate it on PA restart. Flatpak apps have `PULSE_SERVER=unix:/run/flatpak/pulse/native` baked into their sandbox env but the socket is gone. Menu restart reuses the existing sandbox with a stale bind-mount — it does not help.

```bash
# 1. Recreate the socket directory
sudo mkdir -p /run/flatpak/pulse
sudo chown $USER:$USER /run/flatpak /run/flatpak/pulse
ln -s /run/user/1000/pulse/native /run/flatpak/pulse/native
touch /run/flatpak/pulse/config

# 2. Verify connectable
PULSE_SERVER=unix:/run/flatpak/pulse/native pactl info

# 3. Full kill + relaunch (NOT menu restart)
pkill firedragon   # or whichever app, then reopen from launcher
```

## Ghost InputOnly window — XFCE screenshot region tool

xfce4-screenshooter's region-select creates a fullscreen `InputOnly` + `Override Redirect` X window. If the tool crashes mid-selection it stays mapped, invisibly swallowing all clicks and keyboard input. Cursor only flickers briefly on Alt+Tab.

```bash
export DISPLAY=:0 XAUTHORITY=~/.Xauthority
xwininfo -root -children | grep "1920x1080+0+0"
# Note the window ID, confirm it:
xwininfo -id 0x5000004 | grep -E "Class|Override|Map State"
# Should show: InputOnly, Override Redirect State: yes, IsViewable
xdotool windowkill 0x5000004
xsetroot -cursor_name left_ptr   # restore cursor if hidden
```

## Ghost InputOnly window — Xephyr exit without -no-host-grab

Xephyr launched without `-no-host-grab` grabs the host keyboard and pointer. If it exits abnormally the grab is never released and an invisible fullscreen `InputOnly` + `Override Redirect` window remains, swallowing all input.

**Prevention**: always pass `-no-host-grab` — all sanctuary launch scripts in `distrobox.org` include it.

**Recovery** (SSH in or switch to a TTY):

```bash
export DISPLAY=:0 XAUTHORITY=~/.Xauthority
xwininfo -root -children | grep "1920x1080+0+0"
xwininfo -id 0x4e00004 | grep -E "Class|Override|Map State"
xdotool windowkill 0x4e00004
xsetroot -cursor_name left_ptr
```

## xfconf symlink means xfconfd writes directly to DotCortex

The sanctuary-sx launch script symlinks the guest home's `xfce-perchannel-xml` directory to `linux/.config/sanctuary-sx/xfconf/` in the DotCortex tree. Any new app installed in the sanctuary silently creates a channel file in the repo on first xfconf access.

Before any `git add` involving xfconf: run `git status linux/.config/sanctuary-sx/xfconf/` and review new files. Add ephemeral or machine-specific channels to `.gitignore` **before** staging. Never use `git add -A` or broad pathspecs that sweep up xfconf files without review.

## Host X utilities not in Guix container PATH

Tools from the host Debian system (`setxkbmap`, `xrandr`, `xdpyinfo`, etc.) are absent from PATH inside a Guix-backed Distrobox sanctuary. The host filesystem is mounted read-only at `/run/host/`. Any `.desktop` file, shell script, or XDG autostart entry needing host X utilities must use the full path:

```
/run/host/usr/bin/setxkbmap -layout us -variant colemak
/run/host/usr/bin/xrandr --query
```

Bare names fail silently in XDG autostart context (session manager drops the error).

## XFCE 4.20 xfsettingsd silently drops XkbVariant

xfsettingsd applies `XkbLayout` from `keyboard-layout.xml` but discards `XkbVariant` on startup, reverting to base layout (QWERTY for `us`). The Keyboard GUI shows the correct variant but it doesn't take effect.

Fix: XDG autostart `.desktop` entry running `setxkbmap` explicitly — autostart fires after xfsettingsd so it wins. In Guix containers use the full host path:

```ini
[Desktop Entry]
Type=Application
Name=Colemak keyboard layout
Exec=/run/host/usr/bin/setxkbmap -layout us -variant colemak -option terminate:ctrl_alt_bksp
NoDisplay=true
```

For sanctuary-sx this is tangled to `linux/.config/sanctuary-sx/autostart/sanctuary-sx-colemak.desktop`.

## XFCE 4.20 wallpaper folder-picker permanently broken (Xephyr)

The Background settings folder picker fails silently when Xephyr reports the monitor name as `default` — the GUI writes to `monitor0` but xfdesktop reads from `monitordefault`. The wallpaper never changes.

Fix: use `sanctuary-sx-wallpaper <path>`, which writes directly to xfconf at the correct key (`/backdrop/screen0/monitordefault/workspace0/last-image`) via the guest D-Bus session and restarts xfdesktop. Never use the XFCE Background GUI for wallpaper changes inside sanctuary-sx.

## PowerShell (.NET) interactive redraw "smear" — .NET can't find terminfo in the container

Interactive `pwsh`/PSReadLine in a rootless Distrobox sanctuary shows a forward-growing redraw smear: each keystroke reprints the whole line shifted right (`Get-ChildItem` renders as `Get-ChildItemGet-ChildItem…`), backspace doesn't visually erase, but the command still executes correctly. It is **not** the PSReadLine version, prediction, `TERM`, terminal width, or the cursor-position report — those are all red herrings.

Root cause: .NET's `System.Console` finds the terminfo database via `$TERMINFO`, then `~/.terminfo`, then fixed roots (`/usr/share/terminfo`, ...) — it **never** consults `$TERMINFO_DIRS`. Guix sanctuary containers have no `/usr/share/terminfo` tree (the entry lives only under `/run/host/...`), so .NET loads no terminfo, `cup` (CursorAddress) is null, `Console.SetCursorPosition` silently emits nothing while still caching the move, and PSReadLine's full-buffer redraw never repositions to the prompt origin → the smear. CPR (`ESC[6n`) still works because .NET hard-codes it — so the cursor *report* works while cursor *movement* is silently absent.

Fix: export `TERMINFO` at a tree that has an entry for `$TERM` **before** `pwsh` starts (it is cached for the process lifetime). The host terminfo is mounted read-only at `/run/host/usr/share/terminfo` and carries xterm / rxvt-unicode / etc.:

```bash
if [ -d /run/host/usr/share/terminfo ]; then
  export TERMINFO=/run/host/usr/share/terminfo
fi
```

Confirm with strace: `openat(".../terminfo/x/xterm")` succeeds and `write(1, "\33[1;40H")` cursor-address (CUP) writes reappear before each redraw (0 → many). Terminal-agnostic (any `$TERM` whose entry exists in the tree) and PSReadLine-version-independent (bundled 2.3.6 is fine — no module vendoring needed). On a full VM it self-neutralizes: no `/run/host`, and the VM's own `/usr/share/terminfo` satisfies .NET (just ensure terminfo is installed). Applied in `distrobox.org` → the `redstone-9x-pwsh` wrapper.

## IceWM ignores the XDG icon theme, and DROPS toolbar buttons whose icon it cannot find

The same `Icon=` name renders on the Redstone desktop and comes up blank in the Start menu and quick-launch strip. That is not a caching bug, a size bug, or a bad PNG: **pcmanfm (GTK) resolves names out of the Chicago95 XDG theme; IceWM does not.** Every menu icon that appears to work (`firefox_2`, `multimedia`, `system-file-manager`) also exists in some other theme IceWM does read — nothing that lives *only* in Chicago95 ever resolves.

The trap is the symptom. IceWM does not draw a placeholder for an unresolvable icon — it **omits the whole `prog` entry from the toolbar**. So the failure presents as a *missing button*, which reads as "the launcher is broken / the program isn't installed", and sends you debugging PATH instead of icons.

Fix: graft the icons into IceWM's own directory, `~/.icewm/icons/NAME_16x16.png` (and `_32x32`, `_48x48`), which always resolves. `sanctuary-redstone-9x-launch` does this after projecting Chicago95. An absolute path in the `prog` line also works; a bare theme name does not.

Diagnose it with known-good separator icons between the icons under test (`prog "M" firefox_2 …`), so you are counting gaps between markers rather than trying to identify 16px buttons by eye — misreading a low-res crop will send you down a false trail faster than any bad hypothesis.

## `.desktop` `Exec=` splits on whitespace — quote paths with spaces

`Exec=` is not a shell command line; the launcher parses it with `g_shell_parse_argv`, which splits on whitespace exactly like a POSIX shell. RetroPie ports launchers are named like `Ultimate Doom (MP3) (crispy).sh`, so an unquoted `Exec=` resolves `argv[0]` to `.../ports/doom/Ultimate` — and the icon does **nothing at all**: no error, no window, no log line. A desktop icon that silently does nothing is indistinguishable from one nobody has clicked yet, so this can ship and sit there for days.

Quote the path: `Exec="/run/dotcortex/retropie/isos/ports/doom/Ultimate Doom (MP3) (crispy).sh"`. Space *and* parenthesis are reserved characters in the freedesktop spec. Verify by parsing the emitted file the way GLib would (`shlex.split`) and stat-ing `argv[0]` — never by assuming it launches.

## bash DOS-style prompts: literal backslashes in PS1 are read as prompt escapes

A Win9x/Human68k `Z:\path>` prompt built by a function whose output lands in `PS1` (via `PROMPT_COMMAND='PS1="… $(_dospath)> "'`) corrupts on any path segment that starts with a prompt-escape letter: bash re-expands `PS1` and reads `\h \s \d \w \u \H \t …` as hostname/shell/date/cwd/user. `C:\home\share\dotcortex` renders as `C:<hostname>ome<shell>hare<date>otcortex`. It stays hidden until you `cd` above `~` or into a segment like `home`/`share`/`docs`, because `\P`(ictures) and `\>` are not escapes and pass through untouched — so a shallow test looks fine.

Fix: double every backslash the function emits — `printf '%s' "${dos//\\/\\\\}"` — so bash renders each `\\` as one literal `\`. zsh needs no such fix: its prompt escapes are `%`-based, backslashes are literal (verify anyway).

Verification trap (this is what shipped the bug): test the RENDERED prompt with `${PS1@P}` (bash 4.4+ expands PS1 exactly as the prompt engine would), on an escape-triggering path such as `/home` or `cd ..` above the guest home — NEVER `printf '%s' "$PS1"` on a benign path like `~/Pictures`. Inspecting the PS1 string value shows the backslashes intact and passes green while the real prompt is mangled.
