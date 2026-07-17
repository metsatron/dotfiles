;; room-ice2k

;; Build environment for compiling the =ice2k= Windows-component parts-bin (git
;; submodule at =vendor/ice2k=, GPL-2.0, https://github.com/comdlg32/ice2k) inside
;; the =sanctuary-redstone-9x= container.  Not a runtime profile — sourced only
;; during =sanctuary-redstone-9x-ice2k-build= (owned by =sanctuary-ice2k.org=).

;; ice2k reproduces a large set of Windows UI programs — the Run dialog (=rundlg=),
;; Device Manager (=mmc/devmgmt=), the shutdown dialog, control-panel applets
;; (=control/sysdm=, =control/desk=), Minesweeper (=games/winmine=), winver
;; (=ice2kver=), a battery meter, and the =shell/*= services — all built on the
;; **FOX toolkit 1.6** and ice2k's own in-tree libs (=i2klibs/{ini,branding,comctl32}=
;; → =-li2kini -li2kbrand -lctl32=).  Every component Makefile compiles/links via
;; =`fox-config --cflags/--libs`= and uses FOX's =reswrap= resource compiler.

;; Deps mirror ice2k's =installer.sh= apt list, mapped to their Guix equivalents.
;; The bundled upstream projects ice2k also vendors (icewm, xfe, xlockmore, yad) are
;; NOT built here — Guix already packages icewm (room-gaming), xlockmore and yad, so
;; rebuilding them would be redundant; only ice2k's own reproductions are compiled.


;; [[file:../../../../../package-guix-habitat.org::*room-ice2k][room-ice2k:1]]
;; Virtual Habitat — room-ice2k Guix profile
;; Build environment for compiling the ice2k Windows-component parts-bin inside
;; sanctuary-redstone-9x. NOT a runtime profile — sourced only by the build script.
;; Apply: make guix-room-ice2k
(specifications->manifest
 '(
   "gcc-toolchain"   ; gcc/g++, binutils, glibc, libstdc++ — the C/C++ compiler
   "make"            ; GNU make — every component Makefile
   "pkg-config"      ; library detection
   "fox"             ; FOX toolkit 1.6 — provides fox-config, reswrap, libFOX (all components)
   "imlib2"          ; batmeter image loading
   "libserialport"   ; mmc/devmgmt, shell/hotplug (-lserialport)
   "pciutils"        ; libpci for mmc/devmgmt, shell/hotplug (-lpci)
   "libxcomposite"   ; control/desk (-lXcomposite)
   "libxrandr"       ; mmc/devmgmt, shell/hotplug (-lXrandr)
   "libxi"           ; mmc/devmgmt, shell/hotplug (-lXi)
   "libxtst"         ; mmc/devmgmt header <X11/extensions/XTest.h>
   "libxdamage"      ; FOX / composite deps
   "libxfixes"       ; FOX / composite deps
   "libx11"          ; X11 client library
   "libxext"         ; X11 extensions
   "libxpm"          ; X PixMap
   "libxt"           ; X Toolkit Intrinsics
   ;; `fox-config --libs` emits an explicit link line the ice2k Makefiles pass
   ;; verbatim, so ALL of these must be in the profile to link. libpng is the one
   ;; exception: freetype propagates the single consistent libpng, and listing it
   ;; explicitly pulls a SECOND version (1.6.50 vs freetype's 1.6.39) → a
   ;; conflicting-entries error that aborts `guix package`. So: every fox-config
   ;; lib EXCEPT libpng, which rides in on freetype.
   "freetype"        ; -lfreetype (also propagates the one libpng that answers -lpng)
   "fontconfig"      ; -lfontconfig
   "libjpeg-turbo"   ; -ljpeg
   "libtiff"         ; -ltiff
   "mesa"            ; -lGL
   "glu"             ; -lGLU
   "libxft"          ; -lXft
   "libxcursor"      ; -lXcursor
   "zlib"            ; -lz
   "bzip2"           ; -lbz2
   ;; Xfe suite (xfe file manager, xfw Notepad, xfi image viewer, xfp archive) is a
   ;; FOX autotools build; its prebuilt ./configure runs IT_PROG_INTLTOOL + gettext
   ;; unconditionally, so both tools must be present. startup-notification is
   ;; bundled in-tree (../libsn), so no external package is needed for it.
   "gettext"         ; xfe i18n (msgfmt / libintl)
   "intltool"        ; xfe IT_PROG_INTLTOOL
   "git"             ; parts-bin bookkeeping
   "sed"             ; reproducible source patching if needed
   "gawk"            ; GNU awk
   "coreutils"       ; install, mkdir, cp
   "nss-certs"       ; CA certificates
   ))
;; room-ice2k:1 ends here
