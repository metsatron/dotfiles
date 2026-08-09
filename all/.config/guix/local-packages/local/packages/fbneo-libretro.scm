;; libretro-fbneo (CPS / Neo Geo, from source)

;; FinalBurn Neo's libretro port is the approved 2026 aftermarket bus runtime:
;; the full core covers CPS-1, CPS-2, CPS-3, and Neo Geo from one pinned source
;; build.  The game archives remain user-supplied and are audited separately
;; against the active FBNeo DAT before individual catalogue launchers are emitted.

;; SHA256 (nar, git-fetch): =0gyirglbj738v3qhl6xq08c6vbdyrqyxd0992bzrbbni0ywmn933=
;; Upstream: =https://git.libretro.com/libretro/FBNeo=


;; [[file:../../../../../../package-guix-habitat.org::*libretro-fbneo (CPS / Neo Geo, from source)][libretro-fbneo (CPS / Neo Geo, from source):1]]
;;; Local Guix package — libretro-fbneo (CPS / Neo Geo)
;;; Pinned: master @ 8813808d77fe29c9e29970169c80234d13395015
;;; License: FBNeo non-commercial license (bundled src/license.txt)
;;; Provenance: https://git.libretro.com/libretro/FBNeo
;;; Hash verified: 2026-08-02 via `guix hash -x -S nar` on a fresh clone

(define-module (local packages fbneo-libretro)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system copy)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages commencement)  ; gcc-toolchain
  #:use-module (gnu packages perl))

(define-public libretro-fbneo
  (package
    (name "libretro-fbneo")
    (version "0-8813808")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://git.libretro.com/libretro/FBNeo")
             (commit "8813808d77fe29c9e29970169c80234d13395015")))
       (file-name (git-file-name name version))
       (sha256
        (base32 "0gyirglbj738v3qhl6xq08c6vbdyrqyxd0992bzrbbni0ywmn933"))))
    (build-system copy-build-system)
    (arguments
     '(#:phases
       (modify-phases %standard-phases
         (add-after 'unpack 'compile
           (lambda _
             ;; The upstream libretro Makefile ships generated driver and
             ;; dispatch headers in src/dep/generated.  Build the complete
             ;; all-subset core so the same tested .so serves CPS and Neo Geo.
             (invoke "make" "-C" "src/burner/libretro"
                     "CC=gcc" "CXX=g++" "CC_SYSTEM=gcc" "CXX_SYSTEM=g++"
                     "-j" (number->string (parallel-job-count)))
             #t)))
       #:install-plan
       '(("src/burner/libretro/fbneo_libretro.so" "lib/libretro/"))))
    (native-inputs (list gcc-toolchain perl))
    (supported-systems '("x86_64-linux"))
    (synopsis "Libretro core — FinalBurn Neo arcade emulator")
    (description
     "libretro-fbneo builds the official FinalBurn Neo libretro core for the
X68 Expansion Bus CPS-1/CPS-2/CPS-3 branches and the separate Neo Geo arcade
branch.  The core supports ZIP and 7z archives; legally obtained, current
FBNeo-compatible ROM sets must be supplied separately.")
    (home-page "https://git.libretro.com/libretro/FBNeo")
    (license (license:non-copyleft
              "https://github.com/finalburnneo/FBNeo/blob/master/src/license.txt"))))
;; libretro-fbneo (CPS / Neo Geo, from source):1 ends here
