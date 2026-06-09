# Session Memory (auto-updated by Opus, max 2000 chars)

## Session Facts

## Machine Environment Facts

### pvox cross-machine audio (2026-06-10)
pvox on X230 plays to X230 speakers. To play audio on T480s from X230: SSH into T480s and run pvox there directly — HelmCortex is NFS-mounted on T480s. Do not attempt to pipe raw audio across SSH.
`ssh t480s 'XDG_RUNTIME_DIR=/run/user/1000 <awk or cat> | ~/HelmCortex/FORGE/VoxForge/bin/pvox say Claude --stdin'`

### Plank keyboard grab — T480s (2026-06-10)
Plank grabs bare Space/Enter/Escape/arrows via XGrabKey passive grabs when started without xfwm4 registered. Symptom: those keys produce no KeyPress events in XFCE apps (`xev` silent; `xinput test` still fires, confirming the grab is at X11 level). Fix: `pkill plank && desktop:heal` — `desktop:heal` starts xfwm4 before plank.

## User Model (max 1500 chars for this section)

