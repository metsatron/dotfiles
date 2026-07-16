;; RetroPie EmulationStation fork (from source)

;; Guix's main-channel =emulation-station= is the original unmaintained Aloshi
;; upstream (commit-pinned, no release since) — a different, long-diverged
;; lineage from the actively-developed RetroPie fork the =metsatron= ES theme
;; and =es_systems.cfg= actually target. Packaged locally from source instead.

;; Pinned: tag =v2.9.6=, recursive submodule checkout (RetroPie's ES vendors a
;; couple of dependencies as submodules). Same =cmake-build-system= + Boost 1.89
;; compatibility patch Guix's own package needs, since both share the same-era
;; codebase.

;; SHA256 (nar, git-fetch, recursive): =1cgywc43zwagxdzxcdkcpcycd7ls148hi14k4cl6si8q3ryg8k9c=
;; Upstream: =https://github.com/RetroPie/EmulationStation=


;; [[file:../../../../../../package-guix.org::*RetroPie EmulationStation fork (from source)][RetroPie EmulationStation fork (from source):1]]
;;; Local Guix package — RetroPie's EmulationStation fork
;;; Pinned: v2.9.6, recursive submodule checkout
;;; License: Expat (MIT)
;;; Provenance: https://github.com/RetroPie/EmulationStation/releases/tag/v2.9.6
;;; Hash verified: 2026-07-03 via `guix hash -x -S nar` on a fresh recursive clone

(define-module (local packages retropie-emulationstation)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system cmake)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages algebra)     ; eigen
  #:use-module (gnu packages curl)        ; curl
  #:use-module (gnu packages gl)          ; mesa
  #:use-module (gnu packages image)       ; freeimage
  #:use-module (gnu packages linux)       ; alsa-lib
  #:use-module (gnu packages fontutils)   ; freetype
  #:use-module (gnu packages boost)       ; boost
  #:use-module (gnu packages sdl)         ; sdl2
  #:use-module (gnu packages video)       ; vlc — RetroPie's fork hard-requires
                                          ; it for video-preview support (real
                                          ; build error 2026-07-03: Aloshi
                                          ; upstream Guix package doesn't need it,
                                          ; this fork's CMakeLists.txt does)
  #:use-module (gnu packages web)         ; rapidjson
  #:use-module (gnu packages pkg-config)) ; pkg-config — FindVLC.cmake needs it

(define-public retropie-emulationstation
  (package
    (name "retropie-emulationstation")
    (version "2.9.6")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/RetroPie/EmulationStation")
             (commit (string-append "v" version))
             (recursive? #t)))
       (file-name (git-file-name name version))
       (sha256
        (base32 "1cgywc43zwagxdzxcdkcpcycd7ls148hi14k4cl6si8q3ryg8k9c"))))
    (build-system cmake-build-system)
    (arguments
     '(#:tests? #f  ; no test suite
       #:phases
       (modify-phases %standard-phases
         (add-after 'unpack 'boost-compatibility
           (lambda _
             ;; Boost 1.89 no longer provides the system stub — same fix
             ;; Guix's own emulation-station package needs.
             (substitute* "CMakeLists.txt"
               (("Boost REQUIRED COMPONENTS system")
                "Boost REQUIRED COMPONENTS"))
             #t))
         (add-after 'unpack 'fix-missing-ctime-include
           (lambda _
             ;; Real build error 2026-07-03: TimeUtil.h uses `struct tm` but
             ;; only transitively got its forward declaration via <string>'s
             ;; include chain on whatever libstdc++/glibc this fork was
             ;; developed against. This glibc only forward-declares `tm` from
             ;; <wchar.h>, so the field/return-type use of the full struct
             ;; fails to compile — a genuine missing #include in the fork.
             (substitute* "es-core/src/utils/TimeUtil.h"
               (("#include <string>")
                "#include <ctime>\n#include <string>"))
             #t))
         (add-after 'install 'install-resources
           (lambda* (#:key source outputs #:allow-other-keys)
             ;; Real runtime crash 2026-07-06: ES's CMakeLists installs only
             ;; the binary — never the resources/ tree (fonts, frame.png,
             ;; splash.svg, help icons). ES resolves those at runtime via
             ;; getExePath()/resources (i.e. beside the binary) and
             ;; getHomePath()/.emulationstation/resources — both confirmed
             ;; from the binary's own strings. With resources absent the very
             ;; first font/splash texture load fails ("Error - File type
             ;; unknown!") and ES segfaults on the null texture the instant it
             ;; launches (SIGSEGV, exit 139, observed in sanctuary-retropie).
             ;; Copy the source resources/ tree next to the installed binary
             ;; so getExePath()/resources finds it. The git checkout is passed
             ;; to every build phase as #:source.
             (let ((out (assoc-ref outputs "out")))
               (copy-recursively
                (string-append source "/resources")
                (string-append out "/bin/resources")))
             #t)))))
    (native-inputs (list pkg-config))
    (inputs
     (list alsa-lib boost curl eigen freeimage freetype mesa sdl2
           vlc rapidjson))
    (supported-systems '("x86_64-linux"))
    (synopsis "RetroPie's EmulationStation fork — gamepad-first frontend")
    (description
     "RetroPie's EmulationStation fork is a graphical front-end for a large
number of video game console emulators, usable with any game controller that
has at least 4 buttons, with theming support and a game metadata scraper.
This is the actively-maintained RetroPie lineage, not the original
long-unmaintained Aloshi upstream.")
    (home-page "https://github.com/RetroPie/EmulationStation")
    (license license:expat)))
;; RetroPie EmulationStation fork (from source):1 ends here
