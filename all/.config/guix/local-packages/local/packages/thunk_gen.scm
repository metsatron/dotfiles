;; thunk_gen (host thunk generator for FDPP)

;; FDPP 1.10 externalised its host<->DOS thunk generator into =stsp/thunk_gen=
;; (consumed via pkg-config).  A small self-contained meson tool (flex + bison ->
;; C); no dj64/djgpp dependency.


;; [[file:../../../../../../package-guix-habitat.org::*thunk_gen (host thunk generator for FDPP)][thunk_gen (host thunk generator for FDPP):1]]
(define-module (local packages thunk_gen)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system meson)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages))

(define (p specification)
  (specification->package specification))

(define-public thunk_gen
  (package
    (name "thunk-gen")
    (version "1.10-1-g4967a31")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/stsp/thunk_gen")
             (commit "4967a317e97167640d524f66860908fcb0d88fa8")))
       (file-name (git-file-name name version))
       (sha256
        (base32 "1ffby10z0xv8sabf389cdn41k6qzczh285ns4id1rddp89ylsjpc"))))
    (build-system meson-build-system)
    (arguments
     (list #:tests? #f))
    (native-inputs
     (map p '("flex" "bison" "pkg-config")))
    (supported-systems '("x86_64-linux"))
    (home-page "https://github.com/stsp/thunk_gen")
    (synopsis "Thunk generator for the DOSEMU2/FDPP/dj64 toolchain")
    (description
     "thunk_gen is a code generator that produces the host<->DOS thunk glue used
by FDPP and dj64.  It installs a generator binary, a pkg-config module exposing
the generator and its m4/shell helper scripts, and a makefile include consumed
by FDPP's build.")
    (license license:gpl3+)))
;; thunk_gen (host thunk generator for FDPP):1 ends here
