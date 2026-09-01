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
   ;; the pret disassemblies mirrored in HelmCortex NEXUS/git — the Event
   ;; Surface animation-codec ROMs and Emulator Bay cartridges. Guix carries
   ;; only 0.7.0; the disassembly HEADs want 1.0.x, and two of them have NO
   ;; 0.7-compatible revision at all (pokepinball's history jumps rgbds
   ;; 0.5.2→0.8 — 0.7's rewritten link-script grammar hangs rgblink on its
   ;; contents.link; the pokegreen fork was born on 0.9-era pokered). So the
   ;; profile carries the local source build below (local/packages/rgbds-next,
   ;; -L wired on the guix-dev target); matching disassemblies emit
   ;; byte-identical ROMs at any revision, so this only moves the mirrors to
   ;; HEAD. Supersedes the 0.7-pin ruling of 2026-08-28 (msg 1160).
   ;; Approved by Mètsàtron 2026-09-01 (Telegram msg 1585, "let's move to the
   ;; build from source").
   "rgbds@1.0.3"
   ))
;; Guix User profile manifests:2 ends here
