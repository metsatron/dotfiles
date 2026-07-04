;; sanctuary-cde

;; Official CDE 2.5.3 (=cdesktopenv= on SourceForge, released 2025-11-25) is compiled
;; from source inside the container. Source: =cde-2.5.3.tar.gz= — NOT the stale 2012
;; =arcfide/CDesktopEnv= clone. Build with =./autogen.sh && ./configure && make && make install=.
;; Session entrypoint: =<prefix>/bin/Xsession= (NOT =dtlogin=, NOT =startx=).
;; Do NOT use: imake, make World, installCDE, LessTif, libXp.

;; This profile provides the full build toolchain and all CDE library dependencies
;; available in Guix. Missing from Guix: =libutempter= (use =--disable-utmpx= if
;; configure supports it), libXScrnSaver. These are non-critical for a basic CDE
;; desktop in Xephyr; address if configure fails.


;; [[file:../../../../../guix.org::*sanctuary-cde][sanctuary-cde:1]]
;; Virtual Habitat — sanctuary-cde Guix profile
;; CDE 2.5.3 build toolchain and library deps — all sourced from Guix.
;; Install target: ~/.local/share/cde (user-writable, persists in sanctuary home).
;; geogebra-classic is a local package (local/packages/geogebra.scm); the make
;; target passes -L $(LOCAL_PKGS) so the module is visible.
(use-modules (local packages geogebra)
             (gnu packages)            ; specification->package
             (guix transformations))   ; options->transformation

;; rosegarden pulls in dssi, whose *build* phase is fine but whose *check* phase
;; fails: its test (tests/controller.c) compiles with -Werror, and the newer
;; alsa-lib's <alsa/seq_event.h> emits a #warning that -Werror=cpp promotes to a
;; hard error. Disable dssi's tests via a graph-rewriting transformation applied
;; to rosegarden — the library itself builds correctly, so this yields a working
;; rosegarden and keeps the CDE apply chain from aborting. (loom guix:sanctuary-apply
;; is one fail-fast make chain; a dssi failure here blocks every later profile,
;; including room-retropie.)
(define without-dssi-tests
  (options->transformation '((without-tests . "dssi"))))

(manifest
 (cons*
  (package->manifest-entry geogebra-classic)
  (package->manifest-entry
   (without-dssi-tests (specification->package "rosegarden")))
  (manifest-entries
   (specifications->manifest
    '(
      ;; Build toolchain + download/unpack tools
      "autoconf" "automake" "libtool"
      "gcc-toolchain" "make" "m4"
      "bison" "flex" "patch" "git"
      "tar" "curl" "gzip" "pkg-config"
      ;; OpenMotif — the required Motif implementation (verified in Guix)
      "motif"
      ;; X11 libraries
      "libx11" "libxt" "libxmu" "libxft"
      "libxinerama" "libxpm" "libxaw"
      "libxdmcp" "libxrender"
      ;; X11 tools (needed by CDE at build and runtime)
      "sessreg" "xrdb" "xset" "xbitmaps"
      ;; X11 standard utilities (for CDE action database and user tools)
      "xclock"     ; XclockDig action
      "xrefresh"   ; Xrefresh action
      "xdpyinfo"   ; Xdpyinfo action
      "xwininfo"   ; Xwininfo action
      "xlsfonts"   ; Xlsfonts action
      "xprop"      ; Xprop/Window Properties action
      "xwd"        ; Xwd Capture / Xwud Display actions
      "xfd"        ; Font Preview (Xfd) action
      "xfontsel"   ; font browser
      ;; X11 fonts — misc-fixed family for CDE interface font aliases
      "font-misc-misc"
      ;; System libraries
      "linux-pam" "libxcrypt" "libtirpc" "rpcsvc-proto" "rpcbind"
      "net-base" "inetutils" "gawk" "cups"
      "openssl" "tcl" "lmdb" "opensp" "ncompress"
      "oksh"           ; ksh substitute — OpenBSD Korn Shell (ksh not in Guix)
      "perl" "mkfontdir" "bdftopcf"
      ;; X11 extensions
      "libxscrnsaver"
      ;; Media
      "freetype" "libjpeg-turbo" "bzip2"
      ;; ── CDE Application Manager — full suite ─────────────────────────────
      ;; Games — eboard, ktuberling, supertux, xboard in Guix
      ;; NOT in Guix: dreamchess, lbreakout2, powermanga, pychess
      "gcompris-qt"        ; gcompris — educational games for children
      "eboard"             ; chess board GUI (GNUChess/Crafty/Stockfish)
      "ktuberling"         ; KDE potato guy game
      "supertux"           ; 2D Mario-style platform game
      "xboard"             ; X11 chess frontend
      ;; Graphics — gimp, fontforge, inkscape, okular in Guix; geogebra via local pkg above
      ;; NOT in Guix: xv (shareware, non-free license)
      "gimp"               ; GNU Image Manipulation Program
      "fontforge"          ; font editor
      "inkscape"           ; SVG/vector graphics editor
      "okular"             ; KDE document viewer (PDF, PS, ePub, DjVu)
      ;; Internet — firefox, ungoogled-chromium, icedove in Guix
      ;; NOT in Guix: nxclient (NoMachine proprietary), skype (Microsoft proprietary)
      ;; chromium.dt calls chromium-browser; wrapper added in sanctuary-cde-build step 4
      ;; thunderbird.dt calls thunderbird; wrapper added in sanctuary-cde-build step 4
      "firefox"            ; Mozilla Firefox web browser
      "ungoogled-chromium" ; Chromium without Google telemetry (binary: chromium)
      "icedove"            ; Thunderbird email client (Guix libre name; binary: icedove)
      ;; Office — libreoffice covers Base/Calc/Draw/Impress/Math/Writer
      ;; NOT in Guix: Acrobat_Reader (Adobe proprietary), nedit (not packaged)
      "libreoffice"        ; LibreOffice suite (all components)
      "xournal"            ; PDF annotation / handwriting tool (Office + Utilities)
      "xpdf"               ; lightweight PDF viewer (Office + Utilities)
      ;; Multimedia
      ;; NOT in Guix: k9copy (abandoned), xine/xine-ui (only xine-lib; no GUI packaged)
      "pavucontrol"        ; PulseAudio volume control (pavucontrol.dt → PulseAudioCtrl)
      "amarok"             ; KDE music player
      "brasero"            ; GNOME CD/DVD burning
      "k3b"                ; KDE CD/DVD burning
      "rhythmbox"          ; GNOME music player
      ;; rosegarden — added above with without-tests=dssi (see header); its dssi
      ;; dependency's check phase is broken by alsa-lib's -Werror #warning.
      "sound-juicer"       ; GNOME CD ripper
      "vlc"                ; VideoLAN media player
      ;; System
      ;; NOT in Guix: gla (absent from CDE types db — identity unverifiable),
      ;;              firestarter (abandoned GTK1 firewall), pgadmin4 (not packaged),
      ;;              synaptic (Debian APT GUI, inapplicable in Guix container),
      ;;              virtualbox (Oracle proprietary), wicd (abandoned)
      "engrampa"           ; MATE archive manager
      "file-roller"        ; GNOME archive manager
      ;; Utilities
      ;; NOT in Guix: kile (KDE LaTeX editor not packaged),
      ;;              ngv (absent from CDE types db — identity unverifiable)
      "emacs"              ; GNU Emacs text editor
      "gv"                 ; GNU Ghostscript PostScript/PDF viewer
      "texlive-xdvi-bin"   ; xdvi DVI viewer binary (TeX Live 2026)
      "texlive-xdvi"       ; xdvi support files (TeX Live 2026)
      ;; Education (pre-existing)
      "stellarium"         ; planetarium / sky simulation
      "tuxpaint"           ; kids paint program
      ;; Fallback terminal inside the sanctuary
      "xterm"
      )))))
;; sanctuary-cde:1 ends here
