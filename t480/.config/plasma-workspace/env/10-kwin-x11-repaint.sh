# Plasma/SonicDE sources ~/.config/plasma-workspace/env/*.sh before KWin starts.
# The xf86-video-intel DDX was reverted 2026-07-09: it "cured" the modesetting smear
# (X11Libre/xserver#1924 family) only by disabling hardware GL -- AIGLX cannot load the
# i965 driver Mesa 25 removed, dropping the whole session onto llvmpipe (kitty ~400% CPU).
# We are back on the builtin modesetting DDX with hardware iris. CONFIRMED on the live
# session: EGL bypasses the GLX/Present path implicated upstream -- the smear is gone,
# glamor+DRI3 runs on iris, and kitty fell from 411% to 1.8% CPU.
# KWIN_USE_BUFFER_AGE=0 is gone -- it forced full repaints at ~1.9 cores (192.8% -> 0.2%).
export KWIN_OPENGL_INTERFACE=egl
