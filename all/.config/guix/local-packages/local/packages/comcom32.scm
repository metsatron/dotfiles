;; comcom32 (prebuilt DOS shell)

;; DOSEMU2's 32-bit =command.com=-compatible shell.  Building it from source needs
;; a DJGPP cross-toolchain that the pinned Guix channel lacks, so the upstream
;; prebuilt DOS executable is fetched by content hash.  Upstream publishes only a
;; mutable Pages URL (the 0.4 GitHub release carries no assets), and on 2026-07-22
;; they republished the zip — the drift detonated kikin-kushi's first
;; =windows-compat= build (hash mismatch; every machine without a cached store
;; item would have hit it).  The primary URI is therefore a Wayback Machine
;; snapshot of the current zip — timestamped, immutable, verified byte-identical
;; to the live file before pinning — with the live Pages URL kept as fallback
;; mirror.  On the next upstream drift: snapshot the new zip the same way
;; (=curl https://web.archive.org/save/<url>=, verify with =guix hash= against the
;; =id_= raw URL), then bump snapshot URI + hash + version date together.


;; [[file:../../../../../../package-guix-habitat.org::*comcom32 (prebuilt DOS shell)][comcom32 (prebuilt DOS shell):1]]
(define-module (local packages comcom32)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module (guix build-system copy)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages compression))

(define-public comcom32
  (package
    (name "comcom32")
    ;; version = release base + upstream republish date of the prebuilt zip
    ;; (the zip carries no git-describe; the exe inside is dated 2026-07-22)
    (version "0.4-2026.07.22")
    (source
     (origin
       (method url-fetch)
       ;; Immutable Wayback snapshot first (id_ = raw bytes, no rewriting),
       ;; live Pages URL as fallback mirror. See the prose above this block.
       (uri (list "https://web.archive.org/web/20260729080143id_/https://dosemu2.github.io/comcom64/files/comcom32.zip"
                  "https://dosemu2.github.io/comcom64/files/comcom32.zip"))
       (sha256
        (base32 "0jdqr33r340gk5cd93ajvjk4v0q3jqz35zyli4fmql0yxaszwxvs"))))
    (build-system copy-build-system)
    (arguments
     '(#:install-plan
       '(("comcom32.exe" "share/comcom32/"))
       #:phases
       (modify-phases %standard-phases
         (add-after 'install 'add-command-com-alias
           (lambda* (#:key outputs #:allow-other-keys)
             (let ((dir (string-append (assoc-ref outputs "out")
                                       "/share/comcom32")))
               (symlink "comcom32.exe" (string-append dir "/command.com"))))))))
    (native-inputs (list unzip))
    (supported-systems '("x86_64-linux"))
    (home-page "https://github.com/dosemu2/comcom64")
    (synopsis "32-bit command.com shell for DOSEMU2")
    (description
     "comcom32 is DOSEMU2's 32-bit command.com-compatible DOS shell.  This
package installs the prebuilt DOS executable published by the upstream DOSEMU2
project, avoiding a host DJGPP cross-toolchain dependency.")
    (license license:gpl3+)))
;; comcom32 (prebuilt DOS shell):1 ends here
