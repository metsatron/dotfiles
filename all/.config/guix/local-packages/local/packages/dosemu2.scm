;; DOSEMU2 (upstream binary + FDPP + dj64, relocated)

;; DOSEMU2 with dj64 support, so the (dj64-based) =comcom32= shell actually loads.
;; Building the emulator + dj64 runtime from source needs a djgpp-compatible cross
;; dev-suite (=dj64dev=) the pinned channel cannot provide, so this repackages the
;; upstream Launchpad PPA build — the same commit (=7fb9d334a=) that was attempted
;; from source — relocating the =/usr=-baked Ubuntu binaries onto the Guix store
;; with patchelf.  FDPP comes from the source package above (the PPA's kernel/lib
;; pair is internally inconsistent).  The full plugin set is carried so startup is
;; free of dlopen errors.


;; [[file:../../../../../../package-guix-habitat.org::*DOSEMU2 (upstream binary + FDPP + dj64, relocated)][DOSEMU2 (upstream binary + FDPP + dj64, relocated):1]]
(define-module (local packages dosemu2)
  #:use-module (gnu packages)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module (guix build-system gnu)
  #:use-module (guix gexp)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (local packages comcom32)
  #:use-module (local packages fdpp))

(define (p specification)
  (specification->package specification))

;; DOSEMU2 uses a 64-bit dj64 runtime that the pinned Guix channel cannot
;; build from source without a djgpp cross dev-suite (dj64dev).  The upstream
;; project publishes a mutually-compatible binary set on its Launchpad PPA;
;; this package repackages that set (same pattern as comcom32) and relocates
;; the /usr-baked Ubuntu binaries onto the Guix store with patchelf.
(define %ppa
  "https://ppa.launchpadcontent.net/dosemu2/ppa/ubuntu/pool/main")

;; The dosemu2 PPA is a ROLLING pool: superseded .debs are deleted, so a
;; bare %ppa URL rots within weeks (witnessed 2026-07-29 on kikin-kushi's
;; first windows-compat build — the July 15 dosemu2 deb was already gone).
;; PPA-sourced debs therefore pin an immutable Wayback snapshot (id_ = raw
;; bytes) as primary URI, live URL as fallback, same pattern as comcom32.
;; On the next version bump: download the new deb, `guix hash` it, snapshot
;; via https://web.archive.org/save/<url>, verify the id_ snapshot is
;; byte-identical, then update snapshot-ts + filename + hash together.
(define (deb-origin file uri hash)
  (origin
    (method url-fetch)
    (uri uri)
    (file-name file)
    (sha256 (base32 hash))))

(define (ppa-deb-origin file snapshot-ts path hash)
  (deb-origin
   file
   (list (string-append "https://web.archive.org/web/" snapshot-ts "id_/"
                        %ppa path)
         (string-append %ppa path))
   hash))

;; FDPP is NOT taken from the PPA: its jammy pool ships the kernel package
;; (fdpp @9282d8c, May) out of sync with the loader/lib packages
;; (libfdpp35/libfdldr35 @a23897e, July), and the two disagree on the ELF
;; relocation symbol, so the loader aborts on the kernel.  The source-built
;; fdpp package provides a self-consistent kernel + loader + lib with the
;; libfdpp.so.35 / libfdldr.so.35 sonames the dosemu2 binary links against.

(define libdjdev64-deb
  (ppa-deb-origin
   "libdjdev64.deb" "20260729081346"
   "/d/dj64dev/libdjdev64-0_0.4-0~202607211001+202607221038~ubuntu22.04.1_amd64.deb"
   "18n04qazs34mab9mq7sdf86xrvpympvrlx29zn86d2wjjp8mnznm"))

(define libdjstub64-deb
  (ppa-deb-origin
   "libdjstub64.deb" "20260729081352"
   "/d/dj64dev/libdjstub64-0_0.4-0~202607211001+202607221038~ubuntu22.04.1_amd64.deb"
   "0x3gjxvz8ndi8m8fj6xv6pjr20skk1v9h8bpyvclglfczmxfbjx7"))

;; libb64 is a stock Ubuntu-universe library (not in the PPA nor Guix); the
;; term plugin links it.
(define libb64-deb
  (deb-origin
   "libb64.deb"
   (string-append "http://archive.ubuntu.com/ubuntu/pool/universe/libb/"
                  "libb64/libb64-0d_1.2-5build2_amd64.deb")
   "0mwcchngiy3fhf7f6kq8nil9099fcrnzhl5i7hq8604iclq27swz"))

;; libieee1284 (lpt/parallel-port plugin) and libsearpc (searpc IPC plugin)
;; are stock Ubuntu libraries absent from Guix; carrying them lets dosemu2
;; load its full plugin set without dlopen errors at startup.
(define libieee1284-deb
  (deb-origin
   "libieee1284.deb"
   (string-append "http://archive.ubuntu.com/ubuntu/pool/main/libi/"
                  "libieee1284/libieee1284-3_0.2.11-13build1_amd64.deb")
   "0xjkf4sfapk6n90ml4lnjrfa22dap0hpyssjkijajr58miirc7pw"))

(define libsearpc-deb
  (deb-origin
   "libsearpc.deb"
   (string-append "http://archive.ubuntu.com/ubuntu/pool/universe/libs/"
                  "libsearpc/libsearpc1_3.2.0-3_amd64.deb")
   "0iykyxa6bg3sc8ds0bfc4n5bzr50jqpc860g1p9jq8c1g8m5x136"))

(define-public dosemu2
  (package
    (name "dosemu2")
    (version "2.0pre9-10229-g9881d11ef")
    (source
     (ppa-deb-origin
      "dosemu2.deb" "20260729081336"
      "/d/dosemu2/dosemu2_2.0~pre9-10229-9881d11ef+202607281840~ubuntu22.04.1_amd64.deb"
      "07g1hixa0c6z45qi2x36bdl9s7zqilarzsf3v16pxcp90x2s5q34"))
    (build-system gnu-build-system)
    (arguments
     (list
      #:strip-binaries? #f
      #:phases
      #~(modify-phases %standard-phases
          (delete 'bootstrap)
          (delete 'configure)
          (delete 'build)
          (delete 'check)
          ;; Extract every .deb's data tree into a single merged directory.
          (replace 'unpack
            (lambda* (#:key source #:allow-other-keys)
              (mkdir-p "tree")
              (for-each
               (lambda (deb)
                 (mkdir "d")
                 (with-directory-excursion "d"
                   (invoke "ar" "x" deb))
                 (let ((data (car (find-files "d" "^data\\.tar"))))
                   (invoke "tar" "-C" "tree" "-xf" data))
                 (delete-file-recursively "d"))
               (list source
                     #$libdjdev64-deb #$libdjstub64-deb #$libb64-deb
                     #$libieee1284-deb #$libsearpc-deb))
              (chdir "tree")))
          (replace 'install
            (lambda _
              (let ((out #$output))
                ;; usr/{bin,lib,libexec,share} -> $out/...; etc -> $out/etc.
                ;; All plugins are kept; every plugin's library is carried
                ;; below, so dosemu2 loads its full set without errors.
                (copy-recursively "usr" out)
                (when (file-exists? "etc")
                  (copy-recursively "etc" (string-append out "/etc"))))))
          ;; Relocate the Ubuntu ELF binaries onto the Guix store.
          (add-after 'install 'patchelf
            (lambda _
              (let* ((out #$output)
                     (patchelf (string-append
                                #$(file-append (p "patchelf") "/bin/patchelf")))
                     (ld #$(file-append (p "glibc")
                                        "/lib/ld-linux-x86-64.so.2"))
                     (rpath (string-append
                             out "/lib/x86_64-linux-gnu:"
                             out "/lib/dosemu:"
                             #$(file-append fdpp "/lib") ":"
                             #$(file-append (p "glibc") "/lib") ":"
                             #$(file-append (p "gcc-toolchain") "/lib") ":"
                             #$(file-append (p "elfutils") "/lib") ":"
                             #$(file-append (p "readline") "/lib") ":"
                             #$(file-append (p "slang") "/lib") ":"
                             #$(file-append (p "json-c") "/lib") ":"
                             #$(file-append (p "sdl2") "/lib") ":"
                             #$(file-append (p "sdl2-ttf") "/lib") ":"
                             #$(file-append (p "libx11") "/lib") ":"
                             #$(file-append (p "libxext") "/lib") ":"
                             #$(file-append (p "alsa-lib") "/lib") ":"
                             #$(file-append (p "fluidsynth") "/lib") ":"
                             #$(file-append (p "ao") "/lib") ":"
                             #$(file-append (p "gpm") "/lib") ":"
                             #$(file-append (p "libslirp") "/lib") ":"
                             #$(file-append (p "glib") "/lib") ":"
                             #$(file-append (p "jansson") "/lib") ":"
                             #$(file-append (p "fontconfig") "/lib"))))
                ;; Executables need the store interpreter and the rpath;
                ;; shared objects need only the rpath.
                (for-each
                 (lambda (exe)
                   (when (file-exists? exe)
                     (invoke patchelf "--set-interpreter" ld exe)
                     (invoke patchelf "--set-rpath" rpath exe)))
                 (list (string-append out "/libexec/dosemu2/dosemu2.bin")
                       (string-append out "/bin/dosdebug")
                       (string-append out "/bin/mkfatimage16")))
                (for-each
                 (lambda (f) (invoke patchelf "--set-rpath" rpath f))
                 (find-files (string-append out "/lib") "\\.so($|\\.)")))))
          ;; Point the launcher at the store: its libexec, the relocated plugin
          ;; and data dirs, the fdpp kernel, and the comcom32 shell.
          (add-after 'patchelf 'fix-launcher
            (lambda _
              (let ((launcher (string-append #$output "/bin/dosemu")))
                (substitute* launcher
                  (("^libexecdir=/usr/libexec")
                   (string-append "libexecdir=" #$output "/libexec"))
                  (("^    BINARY=\"\\$libexecdir\"/dosemu2/dosemu2.bin")
                   (string-append
                    "    BINARY=\"$libexecdir\"/dosemu2/dosemu2.bin\n"
                    "    OPTS=\"$OPTS --Fplugindir " #$output "/lib/dosemu"
                    " --Flibdir " #$output "/share/dosemu"
                    " --Fcmddir " #$output "/share/dosemu/commands\"")))
                (wrap-program launcher
                  `("PATH" ":" prefix
                    (,(string-append #$(p "coreutils") "/bin")
                     ,(string-append #$(p "util-linux") "/bin")
                     ,(string-append #$(p "kbd") "/bin")))
                  `("FDPP_KERNEL_DIR" =
                    (,(string-append #$(file-append fdpp "/share/fdpp"))))
                  `("DOSEMU2_COMCOM_DIR" =
                    (,(string-append #$comcom32 "/share/comcom32"))))))))))
    (native-inputs
     (map p '("binutils" "tar" "zstd" "patchelf")))
    (inputs
     (append
      (list comcom32 fdpp)
      (map p '("bash-minimal"
               "glibc" "gcc-toolchain" "elfutils" "readline"
               "slang" "json-c"
               ;; graphical / sound / misc plugin libraries
               "sdl2" "sdl2-ttf" "libx11" "libxext" "alsa-lib"
               "fluidsynth" "ao" "gpm" "libslirp" "glib" "jansson"
               "fontconfig"
               ;; launcher runtime helpers
               "coreutils" "util-linux" "kbd"))))
    (supported-systems '("x86_64-linux"))
    (home-page "https://dosemu2.github.io/dosemu2/")
    (synopsis "DOS emulator for GNU/Linux (upstream binary, dj64/FDPP)")
    (description
     "DOSEMU2 runs DOS programs on x86 GNU/Linux.  This package repackages the
upstream Launchpad PPA build of DOSEMU2 together with its FDPP kernel and dj64
runtime, relocated onto the Guix store, and points the launcher at the packaged
comcom32 command shell for a self-contained interactive DOS environment.  The
binary route is used because the dj64 shell requires a dj64-capable emulator
that the pinned Guix channel cannot build from source without a djgpp cross
dev-suite.")
    (license license:gpl2+)))
;; DOSEMU2 (upstream binary + FDPP + dj64, relocated):1 ends here
