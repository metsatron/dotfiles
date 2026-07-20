;; FDPP (DOS kernel, from source)

;; The FreeDOS-derived DOS kernel DOSEMU2 boots.  Built from source (not the PPA):
;; the PPA's jammy pool ships the =fdpp= kernel package out of sync with its
;; =libfdpp35=/=libfdldr35= loader packages, and the two disagree on the ELF
;; relocation symbol — so a source build is the only self-consistent kernel +
;; loader + lib.  Builds with clang 22 once LTO is disabled (Guix's clang has no
;; =LLVMgold.so=) and =thunk_gen= is supplied.


;; [[file:../../../../../../package-guix-habitat.org::*FDPP (DOS kernel, from source)][FDPP (DOS kernel, from source):1]]
(define-module (local packages fdpp)
  #:use-module (gnu packages)
  #:use-module (guix packages)
  #:use-module (guix git-download)
  #:use-module (guix build-system gnu)
  #:use-module (guix gexp)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (local packages thunk_gen))

(define (p specification)
  (specification->package specification))

(define-public fdpp
  (package
    (name "fdpp")
    (version "1.10-78-ge00e886")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/dosemu2/fdpp")
             ;; devel HEAD contemporary with dosemu2 devel @7fb9d33;
             ;; `git describe` -> 1.10-78-ge00e886.  dosemu2 requires
             ;; `fdpp >= 1.7` (src/plugin/fdpp/configure.ac); this yields
             ;; fdpp.pc Version 1.10.
             (commit "e00e886cb44fa8a0ef2e54937f72ea628377f8c4")))
       (file-name (git-file-name name version))
       (sha256
        (base32 "11l7i0x7v5ipgprs794ajjbh6s37ph1rc2y2xhxb3gcvqz0jj07g"))))
    (build-system gnu-build-system)
    (arguments
     (list
      #:tests? #f
      #:make-flags
      #~(list (string-append "PREFIX=" #$output)
              (string-append "LIBDIR=" #$output "/lib")
              (string-append "DATADIR=" #$output "/share")
              (string-append "PKGCONFIGDIR=" #$output "/lib/pkgconfig")
              "DEBUG_MODE=0"
              ;; USE_LTO defaults to 1, which needs LLVMgold.so (absent from
              ;; Guix's clang) or lld.  Disabling LTO keeps the link on the
              ;; Guix-wrapped bfd `ld`, which auto-injects the RUNPATH entries
              ;; that a bare `-fuse-ld=lld` would strip.  Correctness only
              ;; loses the LTO optimisation.
              "USE_LTO=0")
      #:phases
      #~(modify-phases %standard-phases
          (delete 'configure)
          (add-after 'unpack 'patch-build-metadata
            (lambda _
              ;; Guix checkouts carry no .git, so the makefile's
              ;; `git log`/`git describe` version probes fail with 127.
              (substitute* "fdpp/git-rev.sh"
                (("DATE=`git log -1 --format=%cd --date=rfc`")
                 "DATE='Sat, 1 Jan 2022 14:10:53 +0300'"))
              (substitute* "fdpp/makefile"
                (("GIT_DESCRIBE :=.*")
                 "GIT_DESCRIBE := 1.10-78-ge00e886"))
              ;; defs.mak hardcodes `SHELL = /usr/bin/env bash`, absent in
              ;; the build container -> recipe SHELL is 127.  Point it at the
              ;; store bash instead.  (No trailing `$` anchor: substitute*
              ;; retains the newline, so `$` would fail to match.)
              (substitute* "fdpp/defs.mak"
                (("^SHELL = /usr/bin/env bash")
                 (string-append "SHELL = "
                                #$(file-append (p "bash-minimal")
                                               "/bin/bash")))))))))
    (native-inputs
     (cons thunk_gen
           (map p
                '("bash-minimal"
                  "clang-toolchain"
                  "nasm"
                  "bison"
                  "flex"
                  "gawk"
                  "m4"
                  ;; thunk_gen's tg_m4 helper drives autom4te (from autoconf).
                  "autoconf"
                  "pkg-config"))))
    (inputs (list (p "elfutils")))
    (supported-systems '("x86_64-linux"))
    (home-page "https://github.com/dosemu2/fdpp")
    (synopsis "64-bit DOS kernel for DOSEMU2")
    (description
     "FDPP is a FreeDOS-derived DOS kernel ported to modern C++.  It is built
as a user-space library and kernel image for use by DOSEMU2.")
    (license license:gpl3+)))
;; FDPP (DOS kernel, from source):1 ends here
