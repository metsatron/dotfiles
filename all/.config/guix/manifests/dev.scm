;; [[file:../../../../guix.org::*Guix User profile manifests][Guix User profile manifests:2]]
(specifications->manifest
 '(
   "gcc-toolchain"
   "gdb"
   "cmake"
   "pkg-config"
   "meson"
   "ninja"
   "shellcheck"
   "shfmt"
   "bear"
   ;; Builds the ghostel native module (libghostty terminal for Emacs, emacs.org)
   ;; from source via `zig build' — the alternative is M-x ghostel-download-module,
   ;; which loads an unaudited prebuilt .so from a third-party GitHub release into
   ;; the Emacs process. Pinned: ghostel states "requires Zig 0.15.2+" and Zig
   ;; routinely breaks its build API between minors, so take the named version
   ;; rather than Guix's 0.16.0 default. Bump only if the build demands it.
   "zig@0.15.2"
   ))
;; Guix User profile manifests:2 ends here
