;; Maak control plane (Scheme, XDG-friendly)

;; [[file:../../../README.org::*Maak control plane (Scheme, XDG-friendly)][Maak control plane (Scheme, XDG-friendly):1]]
(use-modules (srfi srfi-1)
             (ice-9 popen) (ice-9 rdelim) (ice-9 match) (ice-9 pretty-print))

;; Run one shell string via bash -lc <cmd>, print stdout, return exit code.
(define (sh cmd)
  (let* ((p   (open-pipe* OPEN_READ "bash" "-lc" cmd))
         (out (read-string p))
         (ec  (close-pipe p)))
    (display out)
    ec))

(define (ok? code) (zero? code))
(define (task name desc thunk) (list name desc thunk))
(define (task-name t)  (list-ref t 0))
(define (task-desc t)  (list-ref t 1))
(define (task-thunk t) (list-ref t 2))

(define HOME (or (getenv "HOME") (error "HOME not set")))
(define CORE-PROFILE (string-append HOME "/.guix-extra-profiles/core/core"))

(define (with-core thunk)
  (let* ((cmd (string-append ". \"" CORE-PROFILE "/etc/profile\"; " (thunk))))
    (sh cmd)))

(define tasks
  (list
   (task 'list "List available tasks"
         (lambda ()
           (for-each (lambda (t) (format #t "~a\t~a~%" (task-name t) (task-desc t))) tasks)
           0))
   (task 'all "TOC → tangle → ensure Guix dirs" (lambda () (sh "make all")))
   (task 'stow "Safe stow (backup real files, then stow)" (lambda () (sh "make safe-stow")))
   (task 'profiles "Build core+dev profiles" (lambda () (sh "make guix-core guix-dev")))
   (task 'guix-core "Build core profile from manifest" (lambda () (sh "make guix-core")))
   (task 'guix-pull "guix pull (update channels)" (lambda () (sh "make guix-pull")))
   (task 'bridge "Apply Flatpak fonts/cursors bridge" (lambda () (sh "make bridge-flatpak")))
   (task 'x11-apply "Re-stow think/.xsessionrc & friends" (lambda () (sh "make x11-apply")))
   (task 'health "Show registrar, GTK module, and nvim path"
         (lambda ()
           (sh "pgrep -af appmenu-registrar || echo 'registrar: (none)'")
           (sh "printf 'GTK_MODULES=%s\\n' \"${GTK_MODULES:-}\"")
           (with-core (lambda () "command -v nvim; nvim --version | sed -n '1,2p'"))
           0))
   (task 'which-nvim "Show nvim location and version"
         (lambda ()
           (with-core (lambda () "command -v nvim; nvim --version | sed -n '1,2p'"))
           0))
   (task 'inkscape-timecapsule "Hint for running Inkscape from a past generation"
         (lambda ()
           (sh "guix describe --generations; echo 'Usage: guix time-machine --generation=N -- shell --pure inkscape -- inkscape'")
           0))
   ))

(define (mk-guix cmd) (sh (string-append "make -f " HOME "/.dotfiles/all/.mk/guix.mk " cmd)))

(define tasks
  (append tasks
          (list
           (task 'guix:dirs "Ensure ancillary Guix directories"
                 (lambda () (mk-guix "guix-dirs")))

           ;; PULL (does NOT bench)
           (task 'guix:pull "guix pull"
                 (lambda () (mk-guix "guix-pull")))

          ;; PULL bench: prints fastest URL **and caches it**
          (task 'guix:pull-bench
                "Probe guix channel mirrors and print the fastest URL (writes cache)"
                (lambda ()
                  (sh "make -f ~/.dotfiles/all/.mk/guix.mk guix-pull-bench")))

          ;; PULL apply: use cached mirror only (or arg passed through)
          (task 'guix:pull-apply
                "Apply fastest guix pull mirror to ~/.config/guix/channels.scm"
                (lambda ()
                  (sh "~/.dotfiles/all/.local/bin/guix-apply-pull-url")))

           ;; CORE/DEV/Gc (unchanged)
           (task 'guix:core "Build core profile from manifest"
                 (lambda () (mk-guix "guix-core")))
           (task 'guix:dev "Build dev profile (depends on core)"
                 (lambda () (mk-guix "guix-dev")))
           (task 'guix:nonguix "Build dev profile (depends on core)"
                 (lambda () (mk-guix "guix-nonguix")))
           (task 'guix:gc "Collect unreferenced store items (reclaim disk space; safe)"
                 (lambda () (mk-guix "guix-gc")))

           ;; Substitutes: bench+apply (never run on list/all)
           (task 'guix:sub-bench
                 "Benchmark Guix substitute servers and print best order"
                 (lambda ()
                   (sh "make -f ~/.dotfiles/all/.mk/guix-substitutes.mk guix-sub-bench")))

           (task 'guix:sub-apply
                 "Apply the best substitute server order to guix-daemon"
                 (lambda ()
                   (sh "make -f ~/.dotfiles/all/.mk/guix-substitutes.mk guix-sub-apply")))
           )))

;; --- Flatpak control plane via loom ---
(define (mk cmd) (sh (string-append "make -f " HOME "/.dotfiles/all/.mk/flatpak.mk " cmd)))

(define tasks
  (append
   tasks
   (list
    (task 'flatpak:remotes "Ensure remotes (user+system) with clean env"
          (lambda () (mk "flatpak-remotes")))
    (task 'flatpak:capture "Capture live apps → linux/.flatpak/manifest/apps.tsv"
          (lambda () (mk "flatpak-capture")))
    (task 'flatpak:diff "Plan: desired (TSV) vs installed"
          (lambda () (mk "flatpak-diff")))
    (task 'flatpak:sync "Additive apply (no removals)"
          (lambda () (mk "flatpak-sync")))
    (task 'flatpak:apply "Enforce exact match (set ENFORCE/UNINSTALL/FO... vars as needed)"
          (lambda () (mk "flatpak-apply")))
    (task 'flatpak:perms-capture "Capture per-app permissions/overrides"
          (lambda () (mk "flatpak-perms-capture")))
    (task 'flatpak:perms-apply "Apply captured permissions/overrides"
          (lambda () (mk "flatpak-perms-apply")))
    )))

(define (run name)
  (let ((t (find (lambda (t) (eq? (task-name t) name)) tasks)))
    (if t ((task-thunk t))
        (begin (format #t "Unknown task: ~a\n" name) 1))))

;; main: accept either `loom list` or `guile -s ... -- list`
(define (main args)
  (let* ((rest (cdr args))                    ; drop program name
         (rest (if (and (pair? rest)
                         (string=? (car rest) "--"))
                    (cdr rest) rest)))
    (match rest
      (("list")        (run 'list))
      (("help")        (run 'list))
      ((cmd . _more)   (run (string->symbol cmd)))
      (_               (begin
                         (format #t "Usage: loom <task>\nTry: loom list\n")
                         1)))))
;; Maak control plane (Scheme, XDG-friendly):1 ends here
