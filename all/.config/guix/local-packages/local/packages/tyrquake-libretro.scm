;; libretro-tyrquake (Quake 1, from source)

;; TyrQuake is the libretro Quake 1 engine used by the Quake ports. It is absent
;; from both the main Guix channel and nonguix, so this is a local source build
;; using the upstream repository's verified Unix libretro Make target.

;; SHA256 (nar, git-fetch): =19kk4n1jy012d5sd0k0v17547kj5xl6408ljyp4lq0bfj02dx7wk=
;; Upstream: =https://github.com/libretro/tyrquake=


;; [[file:../../../../../../package-guix.org::*libretro-tyrquake (Quake 1, from source)][libretro-tyrquake (Quake 1, from source):1]]
;;; Local Guix package — libretro-tyrquake (Quake 1)
;;; Pinned: master @ 8f1e7dcdcdd10f840b7020ac6701ae62b07c41a4
;;; License: GPL v2 (bundled LICENSE.txt in upstream)
;;; Provenance: https://github.com/libretro/tyrquake
;;; Hash verified: 2026-07-12 via `guix hash -x -S nar` on a fresh clone
;;; Build system verified: upstream root `make platform=unix CC=gcc`

(define-module (local packages tyrquake-libretro)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system copy)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages commencement))  ; gcc-toolchain

(define-public libretro-tyrquake
  (package
    (name "libretro-tyrquake")
    (version "0-8f1e7dc")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/libretro/tyrquake")
             (commit "8f1e7dcdcdd10f840b7020ac6701ae62b07c41a4")))
       (file-name (git-file-name name version))
       (sha256
        (base32 "19kk4n1jy012d5sd0k0v17547kj5xl6408ljyp4lq0bfj02dx7wk"))))
    (build-system copy-build-system)
    (arguments
     '(#:phases
       (modify-phases %standard-phases
         (add-after 'unpack 'compile
           (lambda _
             ;; The current upstream checkout has a root Makefile, not
             ;; Makefile.libretro; its Unix target emits tyrquake_libretro.so.
             (invoke "make" "platform=unix" "CC=gcc")
             #t)))
       #:install-plan
       '(("tyrquake_libretro.so" "lib/libretro/"))))
    (native-inputs (list gcc-toolchain))
    (supported-systems '("x86_64-linux"))
    (synopsis "Libretro core — TyrQuake Quake 1 engine")
    (description
     "libretro-tyrquake is the TyrQuake Quake 1 engine libretro core. Quake
game data files must be supplied separately.")
    (home-page "https://github.com/libretro/tyrquake")
    (license license:gpl2)))
;; libretro-tyrquake (Quake 1, from source):1 ends here
