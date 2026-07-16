;; PowerShell 7.x (binary)

;; Official Microsoft Linux x86_64 release, pinned and hashed.  Uses the nonguix
;; =binary-build-system= (already a configured channel) for ELF interpreter and
;; rpath patching.  The =pwsh= binary is wrapped so =PATH= finds it normally.

;; SHA256 base32: =0nh53w3v9584q98rljjabqpvbkn3mn6ylw8483dg5nd0nwkpkmfg= (v7.4.7)
;; Upstream: =https://github.com/PowerShell/PowerShell/releases=


;; [[file:../../../../../../package-guix-habitat.org::*PowerShell 7.x (binary)][PowerShell 7.x (binary):1]]
;;; Local Guix package — PowerShell 7.x binary
;;; Pinned: v7.4.7 linux-x64 official Microsoft release
;;; License: MIT (Expat)
;;; Provenance: https://github.com/PowerShell/PowerShell/releases/tag/v7.4.7
;;; Hash verified: 2026-06-25 on T480s with `guix hash`

(define-module (local packages powershell)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module (nonguix build-system binary)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages compression)
  #:use-module (gnu packages gcc)
  #:use-module (gnu packages icu4c)
  #:use-module (gnu packages instrumentation)
  #:use-module (gnu packages tls)
  #:use-module (gnu packages base))

(define-public powershell
  (package
    (name "powershell")
    (version "7.4.7")
    (source
     (origin
       (method url-fetch)
       (uri (string-append
             "https://github.com/PowerShell/PowerShell/releases/download/"
             "v" version "/powershell-" version "-linux-x64.tar.gz"))
       (sha256
        (base32 "0nh53w3v9584q98rljjabqpvbkn3mn6ylw8483dg5nd0nwkpkmfg"))))
    (build-system binary-build-system)
    (arguments
     `(#:install-plan
       '(("." "lib/powershell" #:include-regexp (".*")))
       #:patchelf-plan
       '(("pwsh" ("glibc" "gcc:lib")))
       #:phases
       (modify-phases %standard-phases
         (add-after 'unpack 'enter-archive-root
           (lambda _
             ;; The upstream tarball has several top-level directories. Guix's
             ;; unpack phase can leave cwd in Modules/, which drops pwsh from
             ;; the later install-plan.
             (when (and (string=? (basename (getcwd)) "Modules")
                        (file-exists? "../pwsh"))
               (chdir ".."))))
         (add-after 'enter-archive-root 'make-payload-writable
           (lambda* (#:key outputs #:allow-other-keys)
             (for-each make-file-writable (find-files "." "\\.so$"))
             (make-file-writable "pwsh")
             (chmod "pwsh" #o755)))
         (add-after 'install 'patch-native-runpaths
           (lambda* (#:key inputs outputs #:allow-other-keys)
             (let* ((out (assoc-ref outputs "out"))
                    (lib (string-append out "/lib/powershell"))
                    (rpath (string-append
                            lib ":"
                            (assoc-ref inputs "gcc:lib") "/lib:"
                            (assoc-ref inputs "glibc") "/lib:"
                            (assoc-ref inputs "icu4c") "/lib:"
                            (assoc-ref inputs "openssl") "/lib:"
                            (assoc-ref inputs "zlib") "/lib:"
                            (assoc-ref inputs "lttng-ust") "/lib")))
               (for-each
                (lambda (file)
                  (make-file-writable file)
                  (invoke "patchelf" "--set-rpath" rpath file))
                (append (find-files lib "\\.so$")
                        (find-files lib "createdump$")))
               ;; The .NET tracepoint provider depends on liblttng-ust.so.0,
               ;; but current Guix ships liblttng-ust.so.1. PowerShell runs
               ;; without this optional tracing provider.
               (let ((trace-provider
                      (string-append lib "/libcoreclrtraceptprovider.so")))
                 (when (file-exists? trace-provider)
                   (delete-file trace-provider))))))
         (add-after 'install 'create-launcher
           (lambda* (#:key outputs #:allow-other-keys)
             (let* ((out (assoc-ref outputs "out"))
                    (lib (string-append out "/lib/powershell"))
                    (bin (string-append out "/bin")))
               (mkdir-p bin)
               (call-with-output-file (string-append bin "/pwsh")
                 (lambda (port)
                   (format port "#!/bin/sh\nexec ~a/pwsh \"$@\"\n" lib)))
               (chmod (string-append bin "/pwsh") #o755)))))))
    (inputs
     `(("glibc" ,glibc)
       ("gcc:lib" ,gcc "lib")
       ("icu4c" ,icu4c)
       ("lttng-ust" ,lttng-ust)
       ("openssl" ,openssl)
       ("zlib" ,zlib)))
    (supported-systems '("x86_64-linux"))
    (synopsis "PowerShell — cross-platform shell and scripting language")
    (description
     "PowerShell Core is a cross-platform automation and configuration
tool/framework from Microsoft.  This package bundles the official prebuilt
Linux x86_64 release (a .NET 8 self-contained application).")
    (home-page "https://github.com/PowerShell/PowerShell")
    (license license:expat)))
;; PowerShell 7.x (binary):1 ends here
