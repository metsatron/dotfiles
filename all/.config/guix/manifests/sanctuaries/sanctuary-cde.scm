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
   ;; Fallback terminal inside the sanctuary
   "xterm"
   ))
;; sanctuary-cde:1 ends here
