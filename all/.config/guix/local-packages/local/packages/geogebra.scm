;; GeoGebra Classic 5 (binary + bundled Zulu JRE)

;; GeoGebra Classic 5 (Java-based interactive mathematics).  Not in the Guix
;; main channel or nonguix.  Uses the official Linux Portable bundle which ships
;; with Azul Zulu OpenJDK 11.  The bundled JRE ELF binaries and shared libraries
;; are patched for the Guix store via =binary-build-system= and =patchelf-plan=.
;; The JOGL/Giac native libs ship inside the jar files and are extracted at
;; runtime by the patched JVM — no further patching required for them.

;; - Version: =5.2.806.0=
;; - Upstream: =https://download.geogebra.org/installers/5.0/GeoGebra-Linux-Portable-5-2-806-0.tar.bz2=
;; - License: GeoGebra non-commercial free — =https://www.geogebra.org/license=
;; - SHA256 base32: =1jqqjr68p2b3dzm9myfvyiyd8z883faq9hk8y4a26jkfmx8r8srq= (verified 2026-06-26)
;; - Bundled JRE: Azul Zulu OpenJDK 11.0.18 (=zulu11.62.17-ca-jre11.0.18-linux_x64=)
;; - Native deps declared: glibc, gcc:lib, zlib, libx11, libxext, libxrender, libxtst, freetype, alsa-lib


;; [[file:../../../../../../guix.org::*GeoGebra Classic 5 (binary + bundled Zulu JRE)][GeoGebra Classic 5 (binary + bundled Zulu JRE):1]]
;;; Local Guix package — GeoGebra Classic 5
;;; Version: 5.2.806.0 (Linux Portable, bundled Azul Zulu OpenJDK 11.0.18)
;;; License: GeoGebra non-commercial free (https://www.geogebra.org/license)
;;; Provenance: https://download.geogebra.org/installers/5.0/GeoGebra-Linux-Portable-5-2-806-0.tar.bz2
;;; Hash verified: 2026-06-26 on T480s with `guix hash`
;;;
;;; Executable layout (inside tarball):
;;;   GeoGebra-Linux-Portable-5-2-806-0/
;;;     geogebra/geogebra          — bash launcher script (JAVACMD/GG_PATH env-overridable)
;;;     geogebra/*.jar             — Java class libraries (geogebra.jar, geogebra_main.jar, …)
;;;     geogebra/jogl.*-natives-linux-amd64.jar  — JOGL OpenGL native libs inside JAR
;;;     geogebra/javagiac-linux64.jar            — Giac CAS native lib inside JAR
;;;     zulu11.62.17-ca-jre11.0.18-linux_x64/   — bundled Azul Zulu JRE 11
;;;
;;; Patching strategy: binary-build-system patches ELF interpreter + RPATH for
;;; the JRE binaries and .so files.  JOGL/Giac native .so files are extracted
;;; from JARs at runtime by the patched JVM — dlopen() uses the already-running
;;; dynamic linker so no additional patching is required.
;;;
;;; Install to sanctuary-cde profile: loom guix:sanctuary-apply

(define-module (local packages geogebra)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module (nonguix build-system binary)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (gnu packages gcc)
  #:use-module (gnu packages base)
  #:use-module (gnu packages compression)
  #:use-module (gnu packages xorg)
  #:use-module (gnu packages fontutils)
  #:use-module (gnu packages audio)
  #:use-module (gnu packages linux))

(define %gg-release "GeoGebra-Linux-Portable-5-2-806-0")
(define %jre-dir    "zulu11.62.17-ca-jre11.0.18-linux_x64")

;;; JRE ELF binaries that need the interpreter + RPATH patched.
(define %jre-bins
  '("bin/java" "bin/jaotc" "bin/jfr" "bin/jjs"
    "bin/jrunscript" "bin/keytool" "bin/pack200"
    "bin/rmid" "bin/rmiregistry" "bin/unpack200"))

;;; JRE shared libraries that need RPATH patched.
(define %jre-libs
  '("lib/server/libjvm.so"
    "lib/jli/libjli.so"
    "lib/libawt.so"
    "lib/libawt_headless.so"
    "lib/libawt_xawt.so"
    "lib/libdt_socket.so"
    "lib/libfontmanager.so"
    "lib/libfreetype.so"
    "lib/libinstrument.so"
    "lib/libj2gss.so"
    "lib/libjava.so"
    "lib/libjavajpeg.so"
    "lib/libjsound.so"
    "lib/libnet.so"
    "lib/libnio.so"
    "lib/libzip.so"))

(define %native-inputs
  '("glibc" "gcc:lib" "zlib" "libx11" "libxext" "libxrender" "libxtst"
    "freetype" "alsa-lib"))

(define-public geogebra-classic
  (package
    (name "geogebra-classic")
    (version "5.2.806.0")
    (source
     (origin
       (method url-fetch)
       (uri (string-append
             "https://download.geogebra.org/installers/5.0/"
             %gg-release ".tar.bz2"))
       (sha256
        (base32 "1jqqjr68p2b3dzm9myfvyiyd8z883faq9hk8y4a26jkfmx8r8srq"))))
    (build-system binary-build-system)
    (arguments
     ;; '(...) inside quasiquote → (quote ...) in builder → evaluates as data list.
     ;; validate-runpath? #f: JRE libs depend on each other (libjvm.so, libjava.so etc.)
     ;; via the JVM's own dlopen mechanism; the ELF RUNPATH validator cannot follow that.
     ;; LD_LIBRARY_PATH in the wrapper covers all JRE-internal runtime deps.
     `(#:install-plan
       '(("geogebra" "lib/geogebra/jars/geogebra")
         ("zulu11.62.17-ca-jre11.0.18-linux_x64" "lib/geogebra/jre"))
       #:validate-runpath? #f
       #:phases
       (modify-phases %standard-phases
         ;; Replace the binary-build-system patchelf phase with a comprehensive scan
         ;; that covers all JRE ELF files: bins get interpreter + ext RPATH; libs get
         ;; ext RPATH.  JRE-internal deps are resolved at runtime via LD_LIBRARY_PATH.
         (replace 'patchelf
           (lambda* (#:key inputs #:allow-other-keys)
             (use-modules (guix build utils))
             (let* ((jre    "zulu11.62.17-ca-jre11.0.18-linux_x64")
                    (interp (car (find-files (assoc-ref inputs "libc")
                                             "ld-linux.*\\.so")))
                    (ext-rpath
                     (string-join
                      (map (lambda (n)
                             (string-append (assoc-ref inputs n) "/lib"))
                           '("glibc" "gcc:lib" "zlib" "libx11" "libxext"
                             "libxrender" "libxtst" "freetype" "alsa-lib"))
                      ":")))
               (for-each
                (lambda (f)
                  (invoke "patchelf" "--set-interpreter" interp f)
                  (invoke "patchelf" "--set-rpath" ext-rpath f))
                (find-files (string-append jre "/bin") "."))
               (for-each
                (lambda (f)
                  (invoke "patchelf" "--set-rpath" ext-rpath f))
                (find-files (string-append jre "/lib") "\\.so")))))
         (add-after 'install 'create-wrapper
           (lambda* (#:key outputs #:allow-other-keys)
             (let* ((out  (assoc-ref outputs "out"))
                    (bin  (string-append out "/bin"))
                    (jre  (string-append out "/lib/geogebra/jre"))
                    (jars (string-append out "/lib/geogebra/jars/geogebra"))
                    (java (string-append jre "/bin/java")))
               (mkdir-p bin)
               (call-with-output-file (string-append bin "/geogebra")
                 (lambda (port)
                   (format port "#!/bin/sh\n")
                   (format port "# GeoGebra Classic 5 (DotCortex local package)\n")
                   (format port "JRE_LIB='~a/lib'\n" jre)
                   (format port "export LD_LIBRARY_PATH=\"$JRE_LIB:$JRE_LIB/server:$JRE_LIB/jli${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\"\n")
                   (format port "exec env JAVACMD='~a' GG_PATH='~a' '~a/geogebra' \"$@\"\n"
                           java jars jars)))
               (chmod (string-append bin "/geogebra") #o755)))))))
    (inputs
     `(("glibc"      ,glibc)
       ("gcc:lib"    ,gcc "lib")
       ("zlib"       ,zlib)
       ("libx11"     ,libx11)
       ("libxext"    ,libxext)
       ("libxrender" ,libxrender)
       ("libxtst"    ,libxtst)
       ("freetype"   ,freetype)
       ("alsa-lib"   ,alsa-lib)))
    (supported-systems '("x86_64-linux"))
    (synopsis "GeoGebra Classic 5 — interactive mathematics for education")
    (description
     "GeoGebra Classic 5 is an interactive mathematics application combining
geometry, algebra, statistics, and calculus in a single interface.  This local
Guix package bundles the official Linux Portable release with the Azul Zulu
OpenJDK 11 JRE, patched for the Guix store.")
    (home-page "https://www.geogebra.org")
    (license
     (license:fsdg-compatible "https://www.geogebra.org/license"
                               "Non-commercial free licence."))))
;; GeoGebra Classic 5 (binary + bundled Zulu JRE):1 ends here
