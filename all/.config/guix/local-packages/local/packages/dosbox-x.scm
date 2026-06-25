;; DOSBox-X (from source)

;; DOSBox-X is the accuracy-focused DOS/Win9x emulator required for the Redstone
;; gaming wing.  Not in Guix main channel or nonguix — built from source here.
;; Uses GNU build system (autoconf/automake).

;; SHA256 base32: =1w2nvpaz2liq6ykrsif6nhd5shz98kdk992hnmykv7rg9zy4sgbn= (v2026.06.02)
;; Upstream: =https://github.com/joncampbell123/dosbox-x=


;; [[file:../../../../../../guix.org::*DOSBox-X (from source)][DOSBox-X (from source):1]]
;;; Local Guix package — DOSBox-X
;;; Pinned: v2026.06.02 source archive (GitHub auto-tarball)
;;; License: GPL v2+
;;; Provenance: https://github.com/joncampbell123/dosbox-x/releases/tag/dosbox-x-v2026.06.02
;;; Hash verified: 2026-06-25 on T480s with `guix hash`

(define-module (local packages dosbox-x)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module (guix build-system gnu)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages audio)
  #:use-module (gnu packages autotools)
  #:use-module (gnu packages compression)
  #:use-module (gnu packages fontutils)
  #:use-module (gnu packages gl)
  #:use-module (gnu packages pkg-config)
  #:use-module (gnu packages sdl))

(define-public dosbox-x
  (package
    (name "dosbox-x")
    (version "2026.06.02")
    (source
     (origin
       (method url-fetch)
       (uri (string-append
             "https://github.com/joncampbell123/dosbox-x/archive/refs/tags/"
             "dosbox-x-v" version ".tar.gz"))
       (sha256
        (base32 "1w2nvpaz2liq6ykrsif6nhd5shz98kdk992hnmykv7rg9zy4sgbn"))))
    (build-system gnu-build-system)
    (arguments
     '(#:configure-flags
       '("--enable-sdl2" "--disable-sdl3"
         "--disable-debug"
         "--enable-silent-rules")
       #:phases
       (modify-phases %standard-phases
         (add-before 'configure 'bootstrap
           (lambda _
             (invoke "sh" "autogen.sh"))))))
    (native-inputs
     (list autoconf automake libtool pkg-config))
    (inputs
     (list alsa-lib
           fluidsynth
           libpng
           mesa
           sdl2
           sdl2-net
           zlib))
    (synopsis "DOS/Win9x emulator with accurate hardware and Win9x support")
    (description
     "DOSBox-X is a fork of DOSBox with extensive enhancements for DOS and
early Windows compatibility.  It adds Win9x emulation, improved hardware
accuracy, and a broader range of emulated sound cards.  Required for the
Redstone 9X gaming sanctuary.")
    (home-page "https://dosbox-x.com")
    (license license:gpl2+)))
;; DOSBox-X (from source):1 ends here
