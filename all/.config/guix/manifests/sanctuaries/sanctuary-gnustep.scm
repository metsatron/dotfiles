;; sanctuary-gnustep

;; Window Maker is available in Guix (=windowmaker= 0.96.0), as are a handful of dockapps and FSViewer (NeXT FileViewer-style file manager — holds the Workspace Manager seat until GWorkspace lands). Full GNUstep runtime (gnustep-base, gnustep-gui, gnustep-back) is not in Guix channels — built from source in-guest by =sanctuary-gnustep-build= (Phase B; see =sanctuary-gnustep.org=). Dockapps Guix lacks (asclock, wmmon, wmmemload, wmnet, wmmoonclock — checked 2026-07-30) are built in-guest too.


;; [[file:../../../../../package-guix-habitat.org::*sanctuary-gnustep][sanctuary-gnustep:1]]
;; Virtual Habitat — sanctuary-gnustep Guix profile
;; Window Maker + dockapps + FSViewer from Guix. GNUstep runtime (base/gui/back)
;; not in Guix channels; compiled from source in-guest (sanctuary-gnustep-build).
(specifications->manifest
 '(
   "windowmaker"    ; classic NeXT-style WM — in Guix 0.96.0
   "xterm"          ; fallback terminal inside the sanctuary
   "fsviewer"       ; NeXT FileViewer-style file manager (0.2.7)
   "wmclock"        ; dock clock (asclock heir until asclock is built in-guest)
   "wmcpuload"      ; CPU load dock tile
   "wmbattery"      ; battery dock tile
   "wmnd"           ; network dock tile
   "wmamixer"       ; audio mixer dock tile (undocked by default; root-menu launch)
   "font-tex-gyre"  ; TeX Gyre Heros — Helvetica-metric titlebar/menu font
   ;; ── GNUstep source-build toolchain (sanctuary-gnustep-build, Phase B) ──
   ;; No gcc-objc in Guix → the runtime is clang + libobjc2 (ng-gnu-gnu combo).
   "clang-toolchain" ; Objective-C compiler for the ng runtime
   "libobjc2"       ; GNUstep ObjC2 runtime (2.2.1)
   "autoconf"       ; Emacs' Git checkout generates configure via autogen.sh
   "texinfo"        ; Emacs configure requires makeinfo for the manual tree
   "make"           ; GNU make (gnustep-make is built from source, 2.9.3)
   "ncurses"        ; Emacs configure and terminal support need tputs
   "pkg-config"
   "tar" "gzip"     ; install steps (manpage compression) need them in-guest
   "libffi"         ; NSInvocation / DO forwarding
   "libxml2" "gnutls" "icu4c" "zlib"     ; gnustep-base
   "curl"           ; libcurl — hard dep of base's ObjC-2.0 toolchain path
   "cairo"          ; gnustep-back backend — propagates freetype/fontconfig/libpng
   "libx11" "libxext" "libxrender" "libxt" ; X11 for back (Xt required by x11 server)
   "libjpeg-turbo" "libtiff"             ; gnustep-gui image reps (libpng via cairo)
   ))
;; sanctuary-gnustep:1 ends here
