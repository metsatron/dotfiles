;; libretro-prboom (Doom, from source)

;; PrBoom is the libretro Doom engine used by the Doom and Freedoom ports. It is
;; absent from both the main Guix channel and nonguix, so this is a local source
;; build using the upstream repository's verified Unix libretro Make target.

;; SHA256 (nar, git-fetch): =17mwgh24jw08i30jim1j63356qql0j8d20wxxdgh9r6bainp6m3q=
;; Upstream: =https://github.com/libretro/libretro-prboom=


;; [[file:../../../../../../package-guix-habitat.org::*libretro-prboom (Doom, from source)][libretro-prboom (Doom, from source):1]]
;;; Local Guix package — libretro-prboom (Doom)
;;; Pinned: master @ 31563d6e65faa6b9b7e975754d2062370bba4342
;;; License: GPL v2 (bundled COPYING in upstream)
;;; Provenance: https://github.com/libretro/libretro-prboom
;;; Hash verified: 2026-07-12 via `guix hash -x -S nar` on a fresh clone
;;; Build system verified: upstream root `make platform=unix CC=gcc`

(define-module (local packages prboom-libretro)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system copy)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages commencement))  ; gcc-toolchain

(define-public libretro-prboom
  (package
    (name "libretro-prboom")
    (version "0-31563d6")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/libretro/libretro-prboom")
             (commit "31563d6e65faa6b9b7e975754d2062370bba4342")))
       (file-name (git-file-name name version))
       (sha256
        (base32 "17mwgh24jw08i30jim1j63356qql0j8d20wxxdgh9r6bainp6m3q"))))
    (build-system copy-build-system)
    (arguments
     '(#:phases
       (modify-phases %standard-phases
         (add-after 'unpack 'compile
           (lambda _
             ;; The current upstream checkout has a root Makefile, not
             ;; Makefile.libretro; its Unix target emits prboom_libretro.so.
             (invoke "make" "platform=unix" "CC=gcc")
             #t)))
       #:install-plan
       '(("prboom_libretro.so" "lib/libretro/"))))
    (native-inputs (list gcc-toolchain))
    (supported-systems '("x86_64-linux"))
    (synopsis "Libretro core — PrBoom Doom engine")
    (description
     "libretro-prboom is the PrBoom Doom engine libretro core. Doom,
Freedoom, and other IWAD data files must be supplied separately.")
    (home-page "https://github.com/libretro/libretro-prboom")
    (license license:gpl2)))
;; libretro-prboom (Doom, from source):1 ends here
