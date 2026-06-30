---
name: sanctuary-gotchas
description: Sanctuary and XFCE gotchas — Xephyr ghost InputOnly window, XFCE screenshot ghost, Flatpak PulseAudio audio dead, xfconf symlink DotCortex, setxkbmap XkbVariant xfsettingsd, host X utilities Guix container PATH, wallpaper xfdesktop
model: claude-haiku-4-5-20251001
---

# Sanctuary Gotchas

Covers XFCE, Xephyr, Flatpak, X11, and Distrobox sanctuary issues.

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
