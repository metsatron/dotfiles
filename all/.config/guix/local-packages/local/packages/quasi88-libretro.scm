;; libretro-quasi88 (PC-88, from source)

;; QUASI88's official libretro port — the default DRIVE B (PC-88) disk-game runtime in Godzilla XS.  Tape media (=.t88=, =.cmt=) require standalone QUASI88; the libretro core handles only disk images (=.d88=, =.u88=, =.m3u=).  BSD 3-Clause, no governance concerns.

;; SHA256 (nar, git-fetch): =1cqw7airnd9zwl6nszgg7gni5g24srmzj45bbka499i7y27iqwkf=
;; Upstream: =https://github.com/libretro/quasi88-libretro=


;; [[file:../../../../../../package-guix-habitat.org::*libretro-quasi88 (PC-88, from source)][libretro-quasi88 (PC-88, from source):1]]
;;; Local Guix package — libretro-quasi88 (NEC PC-8801)
;;; Pinned: master @ b5a0e044a914c9a6b8d7b2dd2ddd152f93d35687
;;; License: BSD-3-Clause
;;; Provenance: https://github.com/libretro/quasi88-libretro
;;; Hash verified: 2026-08-05 via `guix hash -x -S nar` on a fresh clone

(define-module (local packages quasi88-libretro)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system copy)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages commencement))  ; gcc-toolchain

(define-public libretro-quasi88
  (package
    (name "libretro-quasi88")
    (version "0-b5a0e04")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/libretro/quasi88-libretro")
             (commit "b5a0e044a914c9a6b8d7b2dd2ddd152f93d35687")))
       (file-name (git-file-name name version))
       (sha256
        (base32 "1cqw7airnd9zwl6nszgg7gni5g24srmzj45bbka499i7y27iqwkf"))))
    (build-system copy-build-system)
    (arguments
     '(#:phases
       (modify-phases %standard-phases
         (add-after 'unpack 'compile
           (lambda _
             (invoke "make" "-j" (number->string (parallel-job-count))
                     "CC=gcc" "CXX=g++")
             #t)))
       #:install-plan
       '(("quasi88_libretro.so" "lib/libretro/"))))
    (native-inputs (list gcc-toolchain))
    (supported-systems '("x86_64-linux"))
    (synopsis "Libretro core — NEC PC-8801 emulator (QUASI88)")
    (description
     "libretro-quasi88 builds the official libretro port of QUASI88, a NEC
PC-8801 series emulator.  Produces quasi88_libretro.so for RetroArch.
Supports disk images (.d88, .u88) and multi-disk playlists (.m3u, up to 6
disks).  Tape media (.t88, .cmt) require standalone QUASI88.  PC-88 BIOS
ROMs must be supplied separately under RetroArch's system/quasi88/
directory.")
    (home-page "https://github.com/libretro/quasi88-libretro")
    (license license:bsd-3)))
;; libretro-quasi88 (PC-88, from source):1 ends here
