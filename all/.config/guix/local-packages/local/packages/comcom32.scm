;; comcom32 (prebuilt DOS shell)

;; DOSEMU2's 32-bit =command.com=-compatible shell.  Building it from source needs
;; a DJGPP cross-toolchain that the pinned Guix channel lacks, so the upstream
;; prebuilt DOS executable is fetched by content hash (a mutable Pages URL — the
;; hash pins the bytes; a future upstream replacement would require refetching).


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
    (version "0.4-70-g433a530")
    (source
     (origin
       (method url-fetch)
       (uri "https://dosemu2.github.io/comcom64/files/comcom32.zip")
       (sha256
        (base32 "1m00ifv1faaz4xmz7726ifw1br2fybhvja4qydlynig844m3m29k"))))
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
