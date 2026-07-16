;; room-fvwm95

;; Build environment for compiling FVWM95 (fork by mintsuki) inside the
;; =sanctuary-redstone-9x= container.  Not a runtime profile — sourced only
;; during =sanctuary-redstone-9x-fvwm95-build=.

;; Build deps match upstream README: =build-essential=, =autoconf=, =automake=,
;; =pkg-config=, =xorg=, =xinit=, =xbitmaps=, =libx11-dev=, =libxt-dev=,
;; =libxext-dev=, =libxpm-dev=, =libreadline-dev=, =libxmu-headers=.
;; All mapped to their Guix equivalents.


;; [[file:../../../../../package-guix-habitat.org::*room-fvwm95][room-fvwm95:1]]
;; Virtual Habitat — room-fvwm95 Guix profile
;; Build environment for compiling FVWM95 inside sanctuary-redstone-9x.
;; NOT a runtime profile — sourced only during the build script.
;; Apply: make guix-room-fvwm95
(specifications->manifest
 '(
   "gcc-toolchain"  ; gcc, binutils, glibc, libstdc++ headers
   "make"           ; GNU make
   "autoconf"       ; autoconf for ./configure
   "automake"       ; automake
   "pkg-config"     ; pkg-config for library detection
   "libx11"         ; X11 client library
   "libxt"          ; X Toolkit Intrinsics
   "libxext"        ; X11 extensions
   "libxpm"         ; X PixMap library
   "readline"       ; GNU readline
   "libxmu"         ; X miscellaneous utilities
   "xbitmaps"       ; X bitmaps (needed for icon includes)
   "git"            ; clone repository
   "sed"            ; for configure patching if needed
   "gawk"           ; GNU awk
   "coreutils"      ; install, mkdir, etc.
   "nss-certs"       ; CA certificates for git clone
   "cmake"          ; CMake — dsdmine (Minesweeper) build system
   "sdl2"           ; SDL2 dev headers — dsdmine build dep
   ))
;; room-fvwm95:1 ends here
