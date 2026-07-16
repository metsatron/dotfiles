;; retropie-tsugaru (FM-TOWNS, CUI only, from source)

;; Tsugaru by captainys — the modern successor to Unz for FM-TOWNS emulation.
;; =Tsugaru_CUI= only: EmulationStation launches emulator binaries directly and
;; has no use for =Tsugaru_GUI=, which would otherwise need a second pinned
;; git-fetch origin for the separate =captainys/public= helper repo — real
;; packaging weight for a binary nothing here would ever call. Upstream also
;; ships a prebuilt Linux zip (=ubuntu_binary_latest.zip=) in its GitHub
;; Releases, but the sovereign default is source: TOWNSEMU is plain CMake with
;; no non-buildable proprietary blob, so there's no reason to prefer an
;; Ubuntu-CI-built binary over building it in the store like everything else
;; here. The binary stays a documented fallback, not the default.

;; SHA256 (nar, git-fetch): =08kggxwaplby90spwjrvpxbzag0fk73fyd55fn9y6rl237b4033l=
;; Upstream: =https://github.com/captainys/TOWNSEMU=


;; [[file:../../../../../../package-guix.org::*retropie-tsugaru (FM-TOWNS, CUI only, from source)][retropie-tsugaru (FM-TOWNS, CUI only, from source):1]]
;;; Local Guix package — Tsugaru_CUI (FM-TOWNS)
;;; Pinned: tag v20260522
;;; License: MIT
;;; Provenance: https://github.com/captainys/TOWNSEMU/releases/tag/v20260522
;;; Hash verified: 2026-07-03 via `guix hash -x -S nar` on a fresh clone
;;; CUI target only — see room-retropie note on why the GUI variant is
;;; deliberately not packaged.

(define-module (local packages tsugaru)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system cmake)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages gl)      ; mesa, glu
  #:use-module (gnu packages linux))  ; alsa-lib

(define-public retropie-tsugaru
  (package
    (name "retropie-tsugaru")
    (version "20260522")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/captainys/TOWNSEMU")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "08kggxwaplby90spwjrvpxbzag0fk73fyd55fn9y6rl237b4033l"))))
    (build-system cmake-build-system)
    (arguments
     '(#:tests? #f
       #:build-type "Release"
       #:phases
       (modify-phases %standard-phases
         (add-before 'configure 'chdir-to-cmake-root
           (lambda _
             ;; TOWNSEMU's CMakeLists.txt lives under src/, not the repo root.
             (chdir "src")
             #t))
         (replace 'build
           (lambda _
             (invoke "cmake" "--build" "." "--target" "Tsugaru_CUI")
             #t))
         (replace 'install
           (lambda* (#:key outputs #:allow-other-keys)
             ;; Real build error 2026-07-03: the binary lands in main_cui/,
             ;; not the build root — confirmed by a full successful compile.
             (let* ((out (assoc-ref outputs "out"))
                    (bin (string-append out "/bin")))
               (mkdir-p bin)
               (install-file "main_cui/Tsugaru_CUI" bin)))))))
    (inputs (list mesa glu alsa-lib))
    (supported-systems '("x86_64-linux"))
    (synopsis "FM-TOWNS emulator (Tsugaru, CUI frontend only)")
    (description
     "Tsugaru is the modern, actively-maintained successor to Unz for
FM-TOWNS emulation.  This package builds only Tsugaru_CUI, the command-line
frontend suitable for launching from EmulationStation — the GUI variant is
deliberately not packaged.  FM-TOWNS ROM dumps and game CD images (ISO/CUE/
MDS) must be supplied separately — none are bundled.")
    (home-page "https://github.com/captainys/TOWNSEMU")
    (license license:expat)))
;; retropie-tsugaru (FM-TOWNS, CUI only, from source):1 ends here
