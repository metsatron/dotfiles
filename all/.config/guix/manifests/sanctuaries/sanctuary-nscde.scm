;; sanctuary-nscde

;; NsCDE (FVWM-based CDE recreation) is compiled from source inside the container by =sanctuary-nscde-build= (see =sanctuary-nscde.org=), together with ksh93u+m — the AT&T ksh93 fork NsCDE hard-requires, absent from Guix (only mksh/oksh clones exist, which upstream rejects). This profile provides the build toolchain, the X headers/libs NsCDE's small C helpers need (libx11/libxext/libxpm), FVWM3 (the window manager NsCDE configures — Guix carries no fvwm2), and the runtime tool set =configure.ac= checks for: xrdb/xset/xprop/xdpyinfo/cpp for X resources, gettext's msgfmt (hard build dep), python with yaml+xdg modules, xdotool, plus the optional-but-wanted extras (stalonetray tray, xsettingsd GTK theme switching, dunst notifications, xscreensaver, rofi, xclip/ImageMagick screenshots). PyQt5 is included: NsCDE's first-run setup and color/style manager tools warn without it.


;; [[file:../../../../../package-guix-habitat.org::*sanctuary-nscde][sanctuary-nscde:1]]
;; Virtual Habitat — sanctuary-nscde Guix profile
;; ksh93u+m + NsCDE build toolchain, FVWM3, and NsCDE runtime tools.
;; Install target: ~/.local/share/NsCDE (+ ~/.local/share/nscde-deps for ksh93).
;; Apply: make guix-sanctuary-nscde  /  loom guix:nscde-apply
(use-modules (gnu packages)
             (gnu packages kde-frameworks)
             (gnu packages qt)
             (guix build-system qt)
             (guix gexp)
             (guix packages)
             (guix utils))

;; Guix's current `kvantum` package is the Qt6 build.  Build the same upstream
;; release once more for Qt5 so NsCDE's PyQt5 tools and Qt5 accessories use the
;; same Commonality engine as the Qt6 KDE games.  The phase below also moves
;; the Qt5 style plugin into the profile's Qt5 plugin tree; without that, an
;; otherwise successful Qt5 build can be invisible to QStyleFactory.
(define kvantum-qt5
  (package
    (inherit kvantum)
    (name "kvantum-qt5")
    (arguments
     (substitute-keyword-arguments (package-arguments kvantum)
       ((#:qtbase old-qtbase) qtbase-5)
       ((#:configure-flags flags #~'())
        #~(cons "-DENABLE_QT5=ON" #$flags))
       ((#:phases phases)
        #~(modify-phases #$phases
            (replace 'patch-style-dir
              (lambda _
                (substitute* "style/CMakeLists.txt"
                  (("\\$\\{KVANTUM_STYLE_DIR\\}")
                   (string-append #$output
                                  "/lib/qt5/plugins/styles")))))))))
    (native-inputs
     (modify-inputs (package-native-inputs kvantum)
       (replace "qttools" qttools-5)))
    (inputs
     (modify-inputs (package-inputs kvantum)
       (replace "kwindowsystem" kwindowsystem-5)
       (replace "qtsvg" qtsvg-5)
       (replace "qtwayland" qtwayland-5)
       (append qtx11extras)))))

(packages->manifest
 (cons kvantum-qt5
       (map specification->package
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
   ;; Private session bus — the launcher wraps the session in dbus-run-session
   ;; so in-room single-instance apps (GIMP, Firefox, LibreOffice) can never
   ;; rendezvous with host instances over the leaked host bus address
   "dbus"
   ;; Qt toolkit commonality — both generations are needed by the modern
   ;; catalogue (Qt5/PyQt5 in NsCDE itself, Qt6 in the KDE game suite).
   ;; qt5ct/qt6ct provide the per-generation platform integration; the two
   ;; native Kvantum builds provide the shared Commonality style engine.
   "qt5ct" "qt6ct" "kvantum"
   ;; ── Application suite ─────────────────────────────────────────────────
   ;; The room must OWN its applications: distrobox bind-mounts the host home,
   ;; so a menu entry for an app missing from this profile falls through to
   ;; the host's binary (and via the host D-Bus, to the host's running
   ;; instance — the GIMP hijack of 2026-07-30). The roster below is the
   ;; hybrid CDE-period room: NsCDE-native tools plus period-style accessories
   ;; and games. Genuine dt* binaries remain owned by sanctuary-cde.
   "gimp"           ; image editor (the reported hijack case)
   "firefox"        ; web browser
   "icedove"        ; mail (Thunderbird libre; front-panel mail slot)
   "libreoffice"    ; office suite
   "vlc"            ; media player
   "emacs"          ; editor
   "pcmanfm"        ; X file manager — first-run setup found none to offer
   ;; Fallback terminal inside the sanctuary (also NsCDE first-setup requirement)
   "xterm"
   ;; NsCDE tool-registry gaps (audit 2026-07-31): appfinder resolves these
   ;; InfoStore slots from app-catalog candidate lists — without a candidate
   ;; on PATH the front-panel/subpanel button is silently dead.
   "pavucontrol"    ; volumectrl slot — Multimedia subpanel Volume Control
   "xcalc"          ; calculator slot — Tools subpanel Calculator
   "arandr"         ; xrandr-GUI slot — Screen Settings subpanel entry
   "xpdf"           ; Office subpanel PDF entries (Motif-native viewer)
   ;; ── Period-style accessories ────────────────────────────────────────────
   "gpaint"         ; MS Paint-era raster editor
   "pluma"           ; MATE text editor — CDE-era Motif/GTK editor role
   "mate-calc"       ; desktop calculator
   "xarchiver"       ; archive manager
   "atril"           ; PDF/PostScript document viewer
   "eom"             ; image viewer
   "abiword"         ; lightweight WordPad-era word processor
   "gnumeric"        ; lightweight Works/Excel-era spreadsheet
   "xfe"             ; FOX file manager with an X11/Explorer lineage
   ;; ── Classic X11 and CDE-period games ────────────────────────────────────
   "xboard"          ; classic X chess frontend
   "eboard"          ; chess board GUI
   "ktuberling"      ; Potato Guy toy/game
   "supertux"        ; classic 2D platform game
   "gcompris-qt"     ; educational game suite
   ;; ── KDE board, card, puzzle, and arcade games ───────────────────────────
   "kmahjongg" "kshisen" "kpat"
   "kreversi" "bovo" "kfourinline" "ksquares"
   "knights" "kigo" "kajongg" "lskat"
   "katomic" "klines" "kmines" "picmi"
   "kblocks" "kbounce" "kbreakout"
   ;; These two data packages are required by the split KDE game resources.
   "libkmahjongg" "libkdegames"
   ;; ── Larger period-style games ───────────────────────────────────────────
   "aisleriot"       ; Solitaire card games
   "gnubg"           ; GNU Backgammon
   "openttd"         ; Transport Tycoon Deluxe lineage
   "openrct2"        ; RollerCoaster Tycoon 2 lineage
   ))))
;; sanctuary-nscde:1 ends here
