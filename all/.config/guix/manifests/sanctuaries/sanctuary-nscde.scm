;; sanctuary-nscde

;; NsCDE (FVWM-based CDE recreation) is compiled from source inside the container by =sanctuary-nscde-build= (see =sanctuary-nscde.org=), together with ksh93u+m — the AT&T ksh93 fork NsCDE hard-requires, absent from Guix (only mksh/oksh clones exist, which upstream rejects). This profile provides the build toolchain, the X headers/libs NsCDE's small C helpers need (libx11/libxext/libxpm), FVWM3 (the window manager NsCDE configures — Guix carries no fvwm2), and the runtime tool set =configure.ac= checks for: xrdb/xset/xprop/xdpyinfo/cpp for X resources, gettext's msgfmt (hard build dep), python with yaml+xdg modules, xdotool, plus the optional-but-wanted extras (stalonetray tray, xsettingsd GTK theme switching, dunst notifications, xscreensaver, rofi, xclip/ImageMagick screenshots). PyQt5 is included: NsCDE's first-run setup and color/style manager tools warn without it.


;; [[file:../../../../../package-guix-habitat.org::*sanctuary-nscde][sanctuary-nscde:1]]
;; Virtual Habitat — sanctuary-nscde Guix profile
;; ksh93u+m + NsCDE build toolchain, FVWM3, and NsCDE runtime tools.
;; Install target: ~/.local/share/NsCDE (+ ~/.local/share/nscde-deps for ksh93).
;; Apply: make guix-sanctuary-nscde  /  loom guix:nscde-apply
(specifications->manifest
 '(
   ;; Build toolchain (ksh93u+m and NsCDE's C helpers; cpp also serves xrdb at runtime)
   "gcc-toolchain" "make" "pkg-config" "git" "nss-certs"
   "tar" "gzip" "sed" "gawk"
   ;; Autotools + m4 + perl: the pinned git checkout's timestamp skew makes
   ;; make regenerate aclocal.m4/Makefile.in (maintainer-mode), which needs
   ;; the full autotools chain at build time.
   "autoconf" "automake" "m4" "perl"
   ;; gettext — msgfmt is a hard configure dependency; gettext(1) is runtime too
   "gettext"
   ;; X headers/libs for NsCDE's compiled helpers (configure: -lX11 -lXext -lXpm)
   "libx11" "libxext" "libxpm"
   ;; Window manager — NsCDE master supports FVWM3 (Guix has no fvwm2)
   "fvwm3"
   ;; Python runtime (NsCDE tools require the yaml and xdg modules; the
   ;; color/style manager tools want PyQt5 — first-run setup warns without it)
   "python" "python-pyyaml" "python-pyxdg" "python-pyqt@5"
   ;; X utilities NsCDE checks for and drives at runtime
   "xrdb" "xset" "xprop" "xdpyinfo" "xdotool" "xrandr" "xrefresh"
   ;; Optional runtime extras NsCDE integrates when present
   "stalonetray"   ; front-panel tray applets
   "xsettingsd"    ; dynamic GTK theme switching
   "dunst"         ; desktop notifications
   "xscreensaver"  ; screen lock/saver
   "rofi"          ; launcher integration
   "xclip"         ; screenshots to clipboard
   "imagemagick"   ; screenshots to file (import/convert)
   ;; Fallback terminal inside the sanctuary (also NsCDE first-setup requirement)
   "xterm"
   ))
;; sanctuary-nscde:1 ends here
