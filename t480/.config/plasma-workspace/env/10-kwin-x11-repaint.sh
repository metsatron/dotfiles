# Plasma/SonicDE sources ~/.config/plasma-workspace/env/*.sh before KWin starts.
# XLibre compositing is RESTORED on this box: the panel/menu smear was the modesetting
# DDX (X11Libre/xserver#1924 family; xlibre-artix/xlibre-video-intel#2), fixed by forcing
# the xf86-video-intel/SNA DDX in /etc/X11/xorg.conf.d (machine-local — see T480 SystemCodex).
# So we no longer disable compositing here. Retained light mitigation: force full repaints.
export KWIN_USE_BUFFER_AGE=0
