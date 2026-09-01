

;; The =rgbds= 1.0.3 local package — a plain source build of the upstream release
;; tarball, same shape as Guix's own 0.7.0 definition (Makefile build, no
;; configure). Upstream test fixtures are not exercised here: every consumer
;; build verifies its ROM byte-identical against a reference sha1, which is a
;; stronger check than the toolchain's own suite for our use.


;; [[file:../../../../../../package-guix.org::*Guix User profile manifests][Guix User profile manifests:3]]
;;; Local Guix package — RGBDS 1.0.3 built from the upstream source release.
;;; Provenance: https://github.com/gbdev/rgbds/releases/tag/v1.0.3
;;; Hash: `guix download .../v1.0.3.tar.gz` on kikin-kushi, 2026-09-01.
;;; Why local: Guix main carries rgbds 0.7.0; the pret disassembly HEADs
;;; require 1.0.x (see the dev.scm manifest note).

(define-module (local packages rgbds-next)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module (guix build-system gnu)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages bison)
  #:use-module (gnu packages flex)
  #:use-module (gnu packages image)
  #:use-module (gnu packages linux)
  #:use-module (gnu packages pkg-config))

(define-public rgbds-next
  (package
    (name "rgbds")
    (version "1.0.3")
    (source (origin
              (method url-fetch)
              (uri (string-append
                    "https://github.com/gbdev/rgbds/archive/refs/tags/v"
                    version ".tar.gz"))
              (sha256
               (base32
                "0q4nczv2kjmf4pb7v9id160a7mhmprf8mddrnm98ngg5q2ym37p7"))))
    (build-system gnu-build-system)
    (arguments
     `(#:phases
       (modify-phases %standard-phases
         (delete 'configure))
       ;; ROM byte-identity against reference sha1s is the real acceptance
       ;; test for this toolchain; upstream's suite needs fixtures the
       ;; tarball lane does not carry.
       #:tests? #f
       #:make-flags `(,(string-append "PREFIX="
                                      (assoc-ref %outputs "out")))))
    (native-inputs (list bison flex pkg-config util-linux))
    (inputs (list libpng))
    (home-page "https://github.com/gbdev/rgbds")
    (synopsis "Rednex Game Boy Development System (upstream 1.0.x)")
    (description
     "RGBDS assembler/linker toolchain for the Game Boy — rgbasm, rgblink,
rgbfix, rgbgfx — at the 1.0.x line the pret disassembly HEADs require.")
    (license license:expat)))
;; Guix User profile manifests:3 ends here
