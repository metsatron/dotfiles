;; [[file:../../../../package-guix.org::*Guix User profile manifests][Guix User profile manifests:2]]
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
   ;; Builds the ghostel native module (libghostty terminal for Emacs, emacs-spacemacs.org)
   ;; from source via `zig build' — the alternative is M-x ghostel-download-module,
   ;; which loads an unaudited prebuilt .so from a third-party GitHub release into
   ;; the Emacs process. Pinned: ghostel states "requires Zig 0.15.2+" and Zig
   ;; routinely breaks its build API between minors, so take the named version
   ;; rather than Guix's 0.16.0 default. Bump only if the build demands it.
   "zig@0.15.2"
   ;; Game Boy assembler/linker toolchain (rgbasm/rgblink/rgbfix) for building
   ;; the pret disassemblies mirrored in HelmCortex NEXUS/git (pokeyellow,
   ;; pokecrystal) — the Event Surface animation-codec ROMs. Guix carries
   ;; 0.7.0 while the disassembly HEADs want 1.0.x; the mirrors are built from
   ;; their last 0.7-compatible revisions instead (matching disassemblies
   ;; produce byte-identical ROMs at any revision), so the Guix version is
   ;; not pinned. Approved by Mètsàtron 2026-08-28 (Telegram msg 1160).
   "rgbds"
   ))
;; Guix User profile manifests:2 ends here
