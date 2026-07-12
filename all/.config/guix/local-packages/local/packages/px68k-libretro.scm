;; libretro-px68k (X68000, from source)

;; The official libretro line for PX68k (Keropi's original X68000 emulator).
;; No upstream releases — built from the tip of =master=, same as several other
;; libretro cores in Guix's own package set.

;; SHA256 (nar, git-fetch): =01pjvr6fxazlpg7gixq591dxiwlr0jwq0n7zvbk5c9sf2kwac3rc=
;; Upstream: =https://github.com/libretro/px68k-libretro=


;; [[file:../../../../../../guix.org::*libretro-px68k (X68000, from source)][libretro-px68k (X68000, from source):1]]
;;; Local Guix package — libretro-px68k (X68000)
;;; Pinned: master @ 45dfd4005434d1199b01fb74a5371ec9bc513164
;;; License: NonCommercial-style Keropi license (bundled COPYING in upstream)
;;; Provenance: https://github.com/libretro/px68k-libretro
;;; Hash verified: 2026-07-03 via `guix hash -x -S nar` on a fresh clone

(define-module (local packages px68k-libretro)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system copy)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages commencement))  ; gcc-toolchain

(define-public libretro-px68k
  (package
    (name "libretro-px68k")
    (version "0-45dfd40")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/libretro/px68k-libretro")
             (commit "45dfd4005434d1199b01fb74a5371ec9bc513164")))
       (file-name (git-file-name name version))
       (sha256
        (base32 "01pjvr6fxazlpg7gixq591dxiwlr0jwq0n7zvbk5c9sf2kwac3rc"))))
    (build-system copy-build-system)
    (arguments
     '(#:phases
       (modify-phases %standard-phases
         (add-after 'unpack 'compile
           (lambda _
             ;; copy-build-system has no 'build phase of its own — this
             ;; core needs a real compile step before the install plan
             ;; copies the resulting .so into place. gcc-toolchain doesn't
             ;; provide a bare `cc` alias, and the upstream Makefile
             ;; hardcodes CC ?= cc, so override it explicitly.
             (invoke "make" "-f" "Makefile.libretro" "CC=gcc")
             #t)))
       #:install-plan
       '(("px68k_libretro.so" "lib/libretro/"))))
    (native-inputs (list gcc-toolchain))
    (supported-systems '("x86_64-linux"))
    (synopsis "Libretro core — Sharp X68000 emulator (Keropi/PX68k lineage)")
    (description
     "libretro-px68k builds the official libretro line of PX68k, a Sharp
X68000 emulator descended from Keropi's original PX68k.  Produces
px68k_libretro.so for RetroArch/EmulationStation.  X68000 BIOS files must be
supplied separately under RetroArch's system/keropi/ directory — none are
bundled, per upstream's own licensing.")
    (home-page "https://github.com/libretro/px68k-libretro")
    (license (license:non-copyleft
              "https://github.com/libretro/px68k-libretro/blob/master/COPYING"))))
;; libretro-px68k (X68000, from source):1 ends here
