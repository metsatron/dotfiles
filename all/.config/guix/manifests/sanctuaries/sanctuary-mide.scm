;; sanctuary-mide

;; MiDesktop 1.2 (Libranext's KDE 1.1.2 fork) and its Osiris toolkit (Qt 2.3.2 fork) are compiled from source inside the container by =sanctuary-mide-build= (see =sanctuary-mide.org=). This profile provides only the build toolchain and libraries: Osiris builds with meson/ninja and needs freetype, zlib, libpng, libjpeg, Xft, XKB, and GLU; MiDesktop builds with CMake/ninja and adds libtiff, xcb, and gettext. Upstream requires GCC 12+ — the default Guix =gcc-toolchain= satisfies it; if 1998-lineage C++ trips on a too-new GCC, pin =gcc-toolchain@14= (or =@12=) here. Install prefix is the =/opt/kde1= bind volume, not this profile.


;; [[file:../../../../../package-guix-habitat.org::*sanctuary-mide][sanctuary-mide:1]]
;; Virtual Habitat — sanctuary-mide Guix profile
;; Osiris 2.4.4 + MiDesktop 1.2 build toolchain and library deps.
;; Install target: /opt/kde1 (host-backed bind volume — see sanctuary-mide.org).
;; Apply: make guix-sanctuary-mide  /  loom guix:mide-apply
(specifications->manifest
 '(
   ;; Build toolchain
   "gcc-toolchain" "cmake" "ninja" "meson" "make"
   "pkg-config" "git" "gettext" "nss-certs"
   "tar" "gzip"
   ;; Osiris (Qt 2.3.2 fork) library deps. libpng is NOT listed explicitly:
   ;; freetype/fontconfig/libxft propagate libpng@1.6.39 (meets Osiris' 1.6.39
   ;; floor) and an explicit "libpng" resolves to 1.6.50, which conflicts.
   "freetype" "fontconfig" "zlib" "libjpeg-turbo"
   "libxft" "libxrender" "libx11" "libxext" "libxkbfile"
   "libice" "libsm" "libxmu" "mesa" "glu"
   ;; MiDesktop extras. libxcrypt supplies crypt.h (removed from modern
   ;; glibc); linux-pam supplies pam_appl.h — both for base/kcheckpass.
   "libtiff" "libxcb" "libxpm" "libxt"
   "libxcrypt" "linux-pam"
   ;; xprop: launcher polls the KWM_RUNNING root property to gate the session
   ;; start order (kwm must be listening before kpanel/kfm fire their
   ;; fire-and-forget region/module client messages — see sanctuary-mide.org).
   "xprop"
   ;; Fallback terminal inside the sanctuary
   "xterm"
   ))
;; sanctuary-mide:1 ends here
