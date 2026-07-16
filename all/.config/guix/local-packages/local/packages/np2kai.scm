;; retropie-np2kai (PC-98, from source)

;; NP2kai / AZO234 lineage — the actively-maintained Neko Project II kai fork
;; with continued NP21/W revision merges.  Not literal upstream NP21/W
;; (SimK98/np21w) — AZO234/NP2kai is the current target branch.

;; Correction during build-verification (2026-07-03): the earlier research this
;; was scoped from claimed a CMake build with a =BUILD_X=ON= flag producing an
;; =sdlnp21kai= binary. A real clone at the pinned tag has no CMakeLists.txt
;; anywhere — that claim doesn't hold at =rev.22=. The actual Linux build is a
;; plain GNU Makefile at =sdl2/Makefile.unix=, producing a binary named =np2kai=.
;; Packaged accordingly; the =cmake=/=BUILD_X= framing is wrong and dropped.

;; SHA256 (nar, git-fetch): =0kxysxhx6jyk82mx30ni0ydzmwdcbnlxlnarrlq018rsnwb4md72=
;; Upstream: =https://github.com/AZO234/NP2kai=


;; [[file:../../../../../../package-guix-habitat.org::*retropie-np2kai (PC-98, from source)][retropie-np2kai (PC-98, from source):1]]
;;; Local Guix package — NP2kai (PC-98 / Neko Project II kai)
;;; Pinned: tag rev.22
;;; License: MAME-derived license mix (see upstream COPYING)
;;; Provenance: https://github.com/AZO234/NP2kai/releases/tag/rev.22
;;; Hash verified: 2026-07-03 via `guix hash -x -S nar` on a fresh clone
;;; Build system verified 2026-07-03: plain Make (sdl2/Makefile.unix), not
;;; CMake — a real clone at this tag has no CMakeLists.txt anywhere.

(define-module (local packages np2kai)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system gnu)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages sdl)         ; sdl2, sdl2-mixer, sdl2-ttf
  #:use-module (gnu packages pkg-config))

(define-public retropie-np2kai
  (package
    (name "retropie-np2kai")
    (version "rev.22")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/AZO234/NP2kai")
             (commit version)))
       (file-name (git-file-name name version))
       (sha256
        (base32 "0kxysxhx6jyk82mx30ni0ydzmwdcbnlxlnarrlq018rsnwb4md72"))))
    (build-system gnu-build-system)
    (arguments
     '(#:tests? #f
       #:phases
       (modify-phases %standard-phases
         (delete 'configure)  ; no configure script on the sdl2/ Make route
         (add-before 'build 'add-sdl2-ttf-and-mixer-includes
           (lambda* (#:key inputs #:allow-other-keys)
             ;; Real build error 2026-07-03: `sdl2-config --cflags` only
             ;; reports base SDL2's include dir — SDL2_ttf and SDL2_mixer are
             ;; separate Guix packages with their own store paths, and this
             ;; Makefile never asks pkg-config for them. CPATH is honored by
             ;; gcc/g++ automatically, no Makefile patch needed. Each of the
             ;; three has its own include/SDL2 subdirectory in the store.
             (setenv "CPATH"
                     (string-append
                      (assoc-ref inputs "sdl2") "/include/SDL2:"
                      (assoc-ref inputs "sdl2-ttf") "/include/SDL2:"
                      (assoc-ref inputs "sdl2-mixer") "/include/SDL2"))
             #t))
         (add-before 'build 'permit-legacy-pointer-casts
           (lambda _
             ;; GCC 14 made both incompatible-pointer-type mismatches and
             ;; implicit function declarations (e.g. bare `rmdir()` without
             ;; <unistd.h>) and int/pointer conversions (an SDL2_ttf
             ;; TTF_GlyphMetrics signature change since this code was
             ;; written) hard errors by default, previously just warnings —
             ;; confirmed by three separate real build failures on this
             ;; ~20-year-old codebase. -std=gnu17 alone does not undo this.
             ;; A command-line `make CFLAGS=…` override doesn't work here —
             ;; GNU Make locks command-line variables against the Makefile's
             ;; own `CFLAGS +=` unless it uses `override`, which this one
             ;; doesn't, so INCFLAGS would silently drop out. Patch the
             ;; flags into the file instead.
             (substitute* "sdl2/Makefile.unix"
               (("COMMONFLAGS \\+= -O2 -DNDEBUG -D_NDEBUG")
                (string-append
                 "COMMONFLAGS += -O2 -DNDEBUG -D_NDEBUG"
                 " -Wno-error=incompatible-pointer-types"
                 " -Wno-error=implicit-function-declaration"
                 " -Wno-error=int-conversion")))
             #t))
         (replace 'build
           (lambda _
             ;; gcc-toolchain provides gcc/g++ but no bare `cc` alias here.
             (invoke "make" "-C" "sdl2" "-f" "Makefile.unix" "CC=gcc")
             #t))
         (replace 'install
           (lambda* (#:key outputs #:allow-other-keys)
             (let* ((out (assoc-ref outputs "out"))
                    (bin (string-append out "/bin")))
               (mkdir-p bin)
               (install-file "sdl2/np2kai" bin)
               #t))))))
    (native-inputs (list pkg-config))
    (inputs (list sdl2 sdl2-mixer sdl2-ttf))
    (supported-systems '("x86_64-linux"))
    (synopsis "PC-98 emulator — Neko Project II kai (NP2kai)")
    (description
     "NP2kai is the actively-maintained Neko Project II kai lineage of the
NEC PC-9800 series emulator, continuing NP21/W revision merges.  Produces the
np2kai SDL2 frontend.  PC-98 BIOS files must be supplied separately — none
are bundled.")
    (home-page "https://github.com/AZO234/NP2kai")
    (license license:expat)))
;; retropie-np2kai (PC-98, from source):1 ends here
