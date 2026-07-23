---
name: sanctuary-gotchas
description: Sanctuary and XFCE gotchas — Xephyr ghost InputOnly window, XFCE screenshot ghost, Flatpak PulseAudio audio dead, xfconf symlink DotCortex, setxkbmap XkbVariant xfsettingsd, host X utilities Guix container PATH, wallpaper xfdesktop
---

# Sanctuary Gotchas

Covers XFCE, Xephyr, Flatpak, X11, and Distrobox sanctuary issues.

## `podman exec` enters as ROOT and poisons the guest home — use `distrobox enter` (sealed 2026-07-14)

`podman exec <sanctuary> …` runs as **container-root**. Anything it writes into the shared guest home lands root-owned, and the desktop user (`metsatron`, uid 1000) can then neither read nor write it. `distrobox enter <sanctuary> -- …` runs as **metsatron** — the user the desktop actually runs as.

This is not theoretical: verifying the Ports menu with `podman exec` created `~/.cache/dotcortex/` root-owned, IceWM could no longer read its own cache, and the menu reported **"Ports unavailable — RetroPie tree not mounted"** while the tree was mounted and fully readable. A cache fault was surfaced to the user as a mount fault, and sent everyone hunting the wrong bug.

It struck again on 2026-07-18: a root-side `podman exec … qt6ct` probe created `~/.config/qt6ct/{colors,qss}` in the guest home. Under `--userns=keep-id`, container-root maps to the **first host subuid** (`grep metsatron /etc/subuid` → e.g. 493216), so on the host those dirs are owned by uid 493216 and the *launcher itself* then dies with `cp: cannot create regular file …: Permission denied` while projecting config — the sanctuary cannot even start. A host-uid in the subuid range on a guest-home file is the fingerprint of this exact mistake.

It struck a third way on 2026-07-22, via a **process** rather than a file: a wallpaper-demo restore step ran `podman exec … pcmanfm --desktop` (no `--user`), so the desktop renderer came up **container-root**. `redstone-9x-scheme-apply` reaps the old renderer with `pkill -u "$(id -u)"` (uid 1000) before starting a fresh one on each theme switch — but it cannot signal a root-owned process, so the stale root `pcmanfm --desktop` survived every switch and fought the new uid-1000 renderer for the root window. The user saw *"wallpapers stopped changing with the theme"*; the real cause was two desktop renderers, one un-reapable. Fingerprint: a guest process whose real uid (`awk '/^Uid:/{print $2}' /proc/PID/status`) is 0 or a subuid while its siblings are 1000. Starting **any** long-lived guest process (renderers, daemons) over bare `podman exec` is the trap, not only file writes — and the cleanup is asymmetric: you must kill the root process from *another* root `podman exec` (uid 1000 cannot signal it), then restart the real one with `--user metsatron`.

- Writing anything into the guest home, or starting any guest process: **always `distrobox enter`** (or `sanctuary-exec`, or `podman exec --user 1000:1000`). Bare `podman exec` is for read-only inspection only.
- After any container work, check your footprint: `find ~/.local/share/dotcortex/guests/<name>/home -not -user metsatron` must return nothing.
- **Recovery** — reclaim from the host via the user namespace (host uid 0 inside `podman unshare` maps back to metsatron): `podman unshare chown -R 0:0 ~/.local/share/dotcortex/guests/<name>/home/<poisoned-path>`. Inspect contents first; qt6ct-style first-launch dirs are empty and safe, but never blind-delete.
- Corollary for tool design: a cache failure must never change what the user sees. If the data source is readable, serve the real content — cached or not. Reserve "unavailable" for the source genuinely being absent, and never write a placeholder INTO a cache (a bad run then poisons every later good one).

## Qt apps ignore SSL_CERT_FILE — an empty /etc/ssl/certs kills every Qt TLS chain (sealed 2026-07-18)

QSslSocket builds its CA store by SCANNING /etc/ssl/certs (and the Debian-path ca-certificates.crt); `SSL_CERT_FILE`/`SSL_CERT_DIR` steer only plain OpenSSL, which Qt bypasses. The sanctuary image ships /etc/ssl/certs present but EMPTY, so every Qt app (Zeal docset downloads) failed with "issuer certificate of a locally looked up certificate could not be found" while a curl test with the same env passed — verifying with curl proves OpenSSL, not Qt; the passing metric lied for two rounds. Fix: root-side symlink of the desktop-common bundle to `/etc/ssl/certs/ca-certificates.crt`, asserted by the launcher each launch.

## Reaching host apps from a sanctuary: host-spawn, ephemeral session bus, -env DISPLAY (sealed 2026-07-18)

`distrobox-host-exec` and `host-spawn` live in /usr/bin, which the sanctuary session PATH does not include — bare names die silently from menus. host-spawn needs the HOST session bus (org.freedesktop.Flatpak): on the sysv fleet that is a dbus-launch socket at an ephemeral /tmp path — never a fixed `/run/user/1000/bus` (which does not even exist here), so the launcher must inject `$DBUS_SESSION_BUS_ADDRESS` into the menu at launch (`@HOST_SESSION_BUS@` token; /tmp is bind-mounted so the path resolves in-guest). host-spawn forwards almost no environment: without `-env DISPLAY` the app opens on the HOST desktop (:0), not the Xephyr — verified both ways. Also: the `/run/user/1000` bind goes stale like any mount-at-start; prefer /tmp-path sockets. Since 2026-07-23 the launchers also project the address as a runtime FILE, `~/.config/sanctuary/host-session-bus` — consumers that run at click time (sanctuary-flatpak-run, lutris-play) read that instead of a baked token.

## GZDoom caches search paths in its ini and shadows a rebuilt engine (sealed 2026-07-23)

GZDoom persists its resource search paths to =~/.config/gzdoom/gzdoom.ini= (=[IWADSearch.Directories]= / =[FileSearch.Directories]=) on first run, then READS them back on every later run — it does not re-add a changed compiled-in default. So rebuilding the engine with a corrected search path does NOT fix an existing install: the stale ini's paths win, and =gzdoom.pk3= stays unfound. Worse, a broken build's garbage path (e.g. a malformed substitution) gets cached and persists across every rebuild. Fix on deploy: clear or migrate the stale ini (=rm ~/.config/gzdoom/gzdoom.ini=, backed up first) so the fixed binary regenerates it clean — verify the *file's* path lines, not a launch. This bites per guest-home too (each has its own ini). Twin gotcha below on why the launch itself can't be trusted as the signal.

## GZDoom writes its errors to its GUI startup window, never stdout — stdout-grep is a lying metric (sealed 2026-07-23)

GZDoom's fatal errors (=Cannot find gzdoom.pk3=, GL failures) go to its GTK startup window and a zenity dialog, NOT stdout. A =timeout gzdoom … > log 2>&1= then =grep -c error log= reads a 0-BYTE log and returns 0 — which looks exactly like "no error" and is not. This produced a false "pk3 error gone" that the user immediately disproved by eye. Do NOT verify GZDoom by grepping stdout. Verify by: (1) the regenerated ini's path lines (file evidence), or (2) =xwininfo= WM_NAME + WM_CLASS + Map State of the actual window — a real game window is titled by the level (e.g. ="DOOM 2: Hell on Earth"=), classed =.gzdoom-real=, IsViewable, at game resolution (1024x819), NOT class =zenity= (error dialog) and NOT 200x100 (the startup/loading window). Distinguish all three; a title string alone lied twice in one session.

## gamemoderun aborts games in the sanctuary Lutris flatpak lane (sealed 2026-07-23)

The Lutris flatpak ships `/app/bin/gamemoderun` and enables it by default when detected, but in the sanctuary launch lane the process talks to the HOST session bus where no `gamemoded` is registered (the guest's daemon lives on its private bus). For SDL-era games the client lib just warns; for Qt/dbus-heavy apps (yuzu, some mono games) libdbus hits `dbus_pending_call_block() ... assertion "pending != NULL"` and ABORTS the game at startup — exit 127/SIGABRT with no game output, easily misread as a missing binary. Since gamemode can never reach its daemon in this lane it provides zero benefit; fix is `system: gamemode: false` in the shared `~/.config/lutris/system.yml`. Found 2026-07-23 when the entire yuzu family "failed" a launch sweep while the same AppImage ran fine exec'd by hand in the same sandbox — 14 of 22 re-tested games flipped to launching on this single toggle.

## Flatpak apps on a private sanctuary bus: glycin dies without org.freedesktop.portal.Flatpak (sealed 2026-07-23)

Sanctuary sessions started under `dbus-run-session` (Redstone IceWM, Godzilla XFCE) get a PRIVATE session bus that does not carry `org.freedesktop.portal.Flatpak` (owned by flatpak-portal — a different name from both `org.freedesktop.Flatpak`/flatpak-session-helper and `org.freedesktop.portal.Desktop`/xdg-desktop-portal). glycin — the GNOME 49 runtime's image loader, used by GTK3 Lutris via its runtime — hard-requires that portal for its `flatpak-spawn --sandbox` loader workers: on the private bus every image load dies and GTK bails out fatally on `image-missing.svg`, leaving a live process with a 10x10 unrendered window (rc alive + window present = the metric lying). Fix: run the outer `flatpak run` against the HOST session bus (read from the projected `~/.config/sanctuary/host-session-bus` file); X11 stays on the Xephyr because `--socket=x11 --env=DISPLAY=` are explicit. Diagnose with `gdbus call … NameHasOwner org.freedesktop.portal.Flatpak` on each bus, not by staring at the crash.

## IceWM menu icons: size mismatch and absolute paths are the blur (sealed 2026-07-18)

IceWM renders menu icons at MenuIconSize and scales whatever it actually loaded. Two traps: (1) the `~/.icewm/icons` graft must ship art at EVERY configured size (`NAME_SxS.png`) — a 16/32/48 graft under MenuIconSize=22 upscales forever; (2) an absolute-path icon BYPASSES lookup entirely, so `apps/16/foo.png` in a 24px menu is blurry no matter what else exists — absolute references must name art at the rendered size. For pixel-art conversions use nearest-neighbor (`ffmpeg -vf "scale=N:N:flags=neighbor"`), pad non-square sources square, and mind AVIF: the alpha is a second stream (`-filter_complex "[0:0][0:1]alphamerge,…"`) — plain `-i` bakes the background opaque.

## A running container never picks up host mounts made after it started (sealed 2026-07-14)

Podman establishes bind mounts **when the container starts**. If the mount source is behind an **autofs** automount (e.g. an NFS tree under `~/mnt/`), and the container starts while that automount is not live, it captures an **empty** bind for the entire life of that run. Nested autofs mounts do **not** propagate into a container's mount namespace — `/home/metsatron/mnt` is simply empty inside the guest.

- `podman start` on an **already-running** container is a **no-op**, so a stale empty bind survives every subsequent launch. It works only by luck — when the container happened to start after the automount was triggered.
- **The remedy is a RESTART, never a recreation.** Trigger the automount host-side first (`stat -L` the path), then stop/start the container. `sanctuary-retropie-bind-ensure` does this, and also recovers a container wedged in `Stopping` (bounded stop → escalate to `podman kill` → confirm `Exited` → start).
- Never tell the user to recreate a sanctuary to fix a stale mount. Recreation is heavyweight, human-gated, and touches the only thing holding their data.

## Distrobox bakes its helper paths into the container at CREATE time (sealed 2026-07-14)

`distrobox create` records the **host paths** of `distrobox-init`, `distrobox-export` and `distrobox-host-exec` as bind mounts inside the container. Move or remove distrobox and every existing container that referenced the old path becomes **unstartable** — `crun: cannot stat …/distrobox-export`.

Removing distrobox from the Guix core manifest (it was destroying rootless podman storage) orphaned three sanctuaries this way. Recreation is the only fix; the bind sources are immutable container config.

It also changed the *contract*: system distrobox (1.8.x) requires ~30 base commands inside the container and shells out to a **package manager** when any are missing — and a Guix image has none. `sanctuary-base` must therefore satisfy that dependency list natively (see `package-guix.org`), and pre-seed `/etc/passwd.done` so `distrobox-init` skips its root-password step (Guix's `passwd` is PAM-linked, the image has no PAM service, and the `chpasswd -e` fallback runs unprivileged and cannot open `/etc/passwd`).

## RetroArch ships an `.info` stub for every core that ever existed — only the `.so` is real (sealed 2026-07-14)

`ls lib/libretro/ | grep prboom` "finds" a core that is not installed: `prboom_libretro.info` is metadata, present for hundreds of cores that are absent. **Only `*_libretro.so` proves a core exists.** This produced a false positive that nearly closed a bug that was still open.

## Single-instance GApplications cross the container wall via /tmp D-Bus sockets (sealed 2026-07-19)

Distrobox sanctuaries share the host's /tmp (bind mount), network namespace, AND pid namespace. Host and guest session-bus sockets both live at `unix:path=/tmp/dbus-*` — mutually connectable. A single-instance GApplication (Pluma, Eye of MATE, mate-system-monitor, most MATE/GNOME apps) launched in-guest can find the HOST's primary instance and hand off: the file opens in the host's editor window. Worse, dconf rides the same bus — a guest MATE app that reaches the host bus reads HOST GSettings, so "why is this app using my host config?" is the same bug. Symptoms are silent (the launch "succeeds", exit 0).

Fix: wrap such launches in `dbus-run-session <app>` — a private bus guarantees a fresh in-guest primary instance and a fresh in-guest dconf-service reading the guest's XDG_CONFIG_HOME. The shared pid namespace is also why `pgrep`/`pkill` from inside a sanctuary match HOST processes (use exact patterns, and the `[b]racket` trick — a pkill of a pattern that appears in your own wrapper's cmdline kills your own process group).

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

**Prevention**: always pass `-no-host-grab` — all sanctuary launch scripts in `sanctuary-distrobox.org` include it.

**Recovery** (SSH in or switch to a TTY):

```bash
export DISPLAY=:0 XAUTHORITY=~/.Xauthority
xwininfo -root -children | grep "1920x1080+0+0"
xwininfo -id 0x4e00004 | grep -E "Class|Override|Map State"
xdotool windowkill 0x4e00004
xsetroot -cursor_name left_ptr
```

## xfconf symlink means xfconfd writes directly to DotCortex

The sanctuary-godzilla-xs launch script symlinks the guest home's `xfce-perchannel-xml` directory to `linux/.config/sanctuary-godzilla-xs/xfconf/` in the DotCortex tree. Any new app installed in the sanctuary silently creates a channel file in the repo on first xfconf access.

Before any `git add` involving xfconf: run `git status linux/.config/sanctuary-godzilla-xs/xfconf/` and review new files. Add ephemeral or machine-specific channels to `.gitignore` **before** staging. Never use `git add -A` or broad pathspecs that sweep up xfconf files without review.

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

For sanctuary-godzilla-xs this is tangled to `linux/.config/sanctuary-godzilla-xs/autostart/sanctuary-godzilla-xs-colemak.desktop`.

## XFCE 4.20 wallpaper folder-picker permanently broken (Xephyr)

The Background settings folder picker fails silently when Xephyr reports the monitor name as `default` — the GUI writes to `monitor0` but xfdesktop reads from `monitordefault`. The wallpaper never changes.

Fix: use `sanctuary-godzilla-xs-wallpaper <path>`, which writes directly to xfconf at the correct key (`/backdrop/screen0/monitordefault/workspace0/last-image`) via the guest D-Bus session and restarts xfdesktop. Never use the XFCE Background GUI for wallpaper changes inside sanctuary-godzilla-xs.

## PowerShell (.NET) interactive redraw "smear" — .NET can't find terminfo in the container

Interactive `pwsh`/PSReadLine in a rootless Distrobox sanctuary shows a forward-growing redraw smear: each keystroke reprints the whole line shifted right (`Get-ChildItem` renders as `Get-ChildItemGet-ChildItem…`), backspace doesn't visually erase, but the command still executes correctly. It is **not** the PSReadLine version, prediction, `TERM`, terminal width, or the cursor-position report — those are all red herrings.

Root cause: .NET's `System.Console` finds the terminfo database via `$TERMINFO`, then `~/.terminfo`, then fixed roots (`/usr/share/terminfo`, ...) — it **never** consults `$TERMINFO_DIRS`. Guix sanctuary containers have no `/usr/share/terminfo` tree (the entry lives only under `/run/host/...`), so .NET loads no terminfo, `cup` (CursorAddress) is null, `Console.SetCursorPosition` silently emits nothing while still caching the move, and PSReadLine's full-buffer redraw never repositions to the prompt origin → the smear. CPR (`ESC[6n`) still works because .NET hard-codes it — so the cursor *report* works while cursor *movement* is silently absent.

Fix: export `TERMINFO` at a tree that has an entry for `$TERM` **before** `pwsh` starts (it is cached for the process lifetime). The host terminfo is mounted read-only at `/run/host/usr/share/terminfo` and carries xterm / rxvt-unicode / etc.:

```bash
if [ -d /run/host/usr/share/terminfo ]; then
  export TERMINFO=/run/host/usr/share/terminfo
fi
```

Confirm with strace: `openat(".../terminfo/x/xterm")` succeeds and `write(1, "\33[1;40H")` cursor-address (CUP) writes reappear before each redraw (0 → many). Terminal-agnostic (any `$TERM` whose entry exists in the tree) and PSReadLine-version-independent (bundled 2.3.6 is fine — no module vendoring needed). On a full VM it self-neutralizes: no `/run/host`, and the VM's own `/usr/share/terminfo` satisfies .NET (just ensure terminfo is installed). Applied in `sanctuary-distrobox.org` → the `redstone-9x-pwsh` wrapper.

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

## `distrobox enter` does NOT reproduce the sanctuary's runtime PATH

The sanctuary's tools (emacs, zsh, `clear`, …) are on PATH because the *launch script* sources the Guix room profiles before starting the desktop — `GUIX_PROFILE=…/desktop-common; . $GUIX_PROFILE/etc/profile`, then room-gaming, room-windows-compat — and every terminal IceWM spawns inherits that environment. A bare `distrobox enter -- bash -lc` does NOT go through the launch script: it sees only `core` + `guix current`, not desktop-common. Asking "is X on PATH in the sanctuary?" that way gives a false negative — it cost two wrong "still not found" verdicts this session on a fix that was actually correct.

To verify sanctuary PATH/env, source the profiles the launch-script way inside the container (or test in a terminal opened inside the running desktop). And note: sourcing a Guix profile's `etc/profile` only adds its `bin/` if `GUIX_PROFILE` is exported *first* — a bare `. etc/profile` is a no-op for PATH. A rebuilt profile also only reaches the user's terminals after a sanctuary relaunch: IceWM-spawned terminals inherit IceWM's stale environment, not the freshly-rebuilt profile.

When a base shell utility is missing in a sanctuary (`clear`, `tput`), the fix is to add its package (`ncurses`) to the shared **desktop-common** manifest in `package-guix.org`, tangle, and rebuild — never an ANSI-escape shim or a per-sanctuary duplicate. desktop-common is sourced by every sanctuary, so one entry fixes all of them.

## Testing sanctuary GUI tools defaults `DISPLAY` to the LIVE `:93` — force an isolated display (sealed 2026-07-17, the wine-desktop invasion)

The redstone env wrappers (`redstone-9x-run`, `redstone-9x-ie`, `redstone-9x-wine`) all do `export DISPLAY="${DISPLAY:-:93}"` — correct for production, a trap for tests. Invoking any of them from a tool subprocess with `DISPLAY` unset falls back to `:93` and throws real windows onto the user's live desktop. A dispatcher-shim test loop did exactly this and papered the running Redstone session with `notepad.exe`/`explorer.exe`/`winecfg.exe` — the "verification must not be indistinguishable from use" rule, in the wine idiom. Before testing anything that sources the sanctuary env: stand up an isolated `Xvfb :97` and set `DISPLAY=:97` **explicitly** (the render harness pattern), or don't launch the GUI tool at all — verify dispatch logic by reading the script / checking symlink targets instead. Never launch wine tools "just to see."

Two compounding traps from the same incident:
- A `Bash(run_in_background)` test that loops over tool names keeps **relaunching** wine even after you kill the visible windows — new PIDs reappear because the *driver* is still alive. Kill the background driver process (find it in `ps` on the host) FIRST; killing the wine children is whack-a-mole.
- `wineserver -k` silently no-ops if its `WINEPREFIX`/socket key doesn't match the running server. To actually clear a stray wine session, SIGKILL by explicit `comm` (`wineserver`, `explorer.exe`, `services.exe`, …) — and only after the relaunch driver is dead, or it respawns instantly.

## The live sanctuary desktop and a headless test share ONE container PID namespace — never blanket-`pkill` (sealed 2026-07-18)

A sanctuary runs the user's live WM (IceWM on `:93`) *inside the container*. A headless render test that starts a second IceWM/rofi on `Xvfb :97` runs in the **same container**, so `distrobox enter … -- pkill -x icewm` / `pkill -x rofi` kills BOTH — the test instance AND the user's live `:93` desktop. Cleanup must target only the test display: iterate `pgrep -x icewm; pgrep -x rofi`, read `/proc/$p/environ`, and `kill` only those with `DISPLAY=:97`. (A blanket pkill got away with it once only because the user had already closed `:93`.) Same rule as the wine cleanup: kill by identity, never by name alone, when a human's session shares the namespace.

## rofi 2.0.0 (Guix): themed-button `action:` fires on CLICK only in `-dmenu` mode (sealed 2026-07-18, the Win95 Run box)

A `.rasi` `button`/custom widget with `action: "kb-custom-1"` etc. does **not** fire on mouse click under `-modes run`/`-show run`/`-show drun` — the click is silently swallowed. It fires correctly under **`-dmenu`**. (Verified exhaustively: real clicks are delivered — dmenu rows double-click-accept — and keyboard bindings work; only the run/drun-mode button click is dead.) So a Win95-style Run box with clickable OK/Cancel/Browse/dropdown buttons must be driven as `-dmenu`, with the wrapper executing the accepted command itself (`setsid bash -c "$out"`) and branching on rofi's exit code (`kb-custom-1`→10, `kb-custom-2`→11, `kb-cancel`→1, accept→0). This is also more Win95-authentic (the real Run box doesn't autocomplete). See `redstone-9x-rofi-run`.

Three attached traps:
- **Empty `-dmenu` list + button click = SIGSEGV (exit 139).** Always feed ≥1 row (append a trailing blank line). The Run history doubles as the row list; the listview stays `enabled: false` to hide it until the ▼ dropdown reveals it via `-theme-str 'listview { enabled: true; }'`.
- **`content:` and `action:` on the SAME rasi line → rofi absorbs `action` into the `content` string** (the button ends up with no action). Put every property on its own line; verify with `rofi -dump-theme`.
- **This build renders no IMAGES in custom theme widgets** — `filename:` icons and `background-image:` both come up blank (text renders fine). So the Win95 corner Run icon and the ▼ dropdown glyph can't be drawn here; the buttons work but stay text/bevel-only. Would need a rofi rebuilt from mainline.
