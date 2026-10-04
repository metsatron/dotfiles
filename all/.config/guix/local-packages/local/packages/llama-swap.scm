

;; The =llama-swap= release binary is packaged locally because Guix has no package
;; for it.  This is the pinned upstream v262 Linux amd64 asset; the tarball is
;; already statically linked, so the binary build system only needs to place the
;; executable and upstream MIT license in the output.


;; [[file:../../../../../../package-guix.org::*Guix User profile manifests][Guix User profile manifests:7]]
;;; Local Guix package — llama-swap v262 release binary.
;;; Pinned: v262 Linux amd64 release asset.
;;; License: MIT (Benson Wong).
;;; Provenance: https://github.com/mostlygeek/llama-swap/releases/tag/v262
;;; SHA256: 871b3ed7891f8ce057428f5a34d38298e06c36c6848c1136e05308eb4303af50

(define-module (local packages llama-swap)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module (nonguix build-system binary)
  #:use-module ((guix licenses) #:prefix license:))

(define-public llama-swap
  (package
    (name "llama-swap")
    (version "262")
    (source
     (origin
       (method url-fetch)
       (uri (string-append
             "https://github.com/mostlygeek/llama-swap/releases/download/v"
             version "/llama-swap_" version "_linux_amd64.tar.gz"))
       (sha256
        (base32 "0l5g0d1yn22kw0v13344qqv6rq4qhb9k8nlg89by130zi7bkw6w7"))))
    (build-system binary-build-system)
    (arguments
     `(#:install-plan
       '(("llama-swap" "bin/llama-swap")
         ("LICENSE.md" "share/doc/llama-swap/LICENSE.md"))))
    (supported-systems '("x86_64-linux"))
    (home-page "https://github.com/mostlygeek/llama-swap")
    (synopsis "Model-swapping proxy for llama.cpp servers")
    (description
     "llama-swap is a proxy that manages multiple llama.cpp servers and
swaps models in and out as requests arrive.")
    (license license:expat)))
;; Guix User profile manifests:7 ends here
