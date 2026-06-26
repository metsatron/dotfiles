# Plasma/SonicDE sources ~/.config/plasma-workspace/env/*.sh before KWin starts.
# XLibre's GL/Present compositing path smears stale buffers across panels and
# menus (X11Libre/xserver#1924). Disable compositing entirely — Mètsàtron uses no
# shadows/blur, so nothing is lost. Remove once XLibre fixes the Present path.
export KWIN_COMPOSE=N
# Retained fallback: if compositing is ever re-enabled, force full repaints.
export KWIN_USE_BUFFER_AGE=0
