;; Maak control plane (Scheme, XDG-friendly)


;; [[file:../../../README.org::*Maak control plane (Scheme, XDG-friendly)][Maak control plane (Scheme, XDG-friendly):1]]
;; Minimal Scheme control plane that orchestrates our Make targets and rituals.
;; We use a wrapper 'loom' to invoke this (see below).

(use-modules (srfi srfi-1)
             (ice-9 popen)
             (ice-9 rdelim)
             (ice-9 match)
             (ice-9 pretty-print))

(define (sh . args)
  (let* ((cmd (string-join args " "))
         (p   (open-pipe* OPEN_READ "bash" "-lc" cmd))
         (out (read-string p))
         (ec  (close-pipe p)))
    (display out)
    ec))

(define (ok? code) (zero? code))
(define (task name desc thunk) (list name desc thunk))
(define (task-name t) (list-ref t 0))
(define (task-desc t) (list-ref t 1))
(define (task-thunk t) (list-ref t 2))

(define HOME (or (getenv "HOME") (error "HOME not set")))
(define CORE-PROFILE (string-append HOME "/.guix-extra-profiles/core/core"))

(define (with-core thunk)
  ;; Ensure our named core profile is sourced for commands launched here.
  (let* ((cmd (string-append ". \"" CORE-PROFILE "/etc/profile\"; " (thunk))))
    (sh "bash" "-lc" cmd)))

(define tasks
  (list
   (task 'list "List available tasks"
         (lambda ()
           (for-each (lambda (t)
                       (format #t "~a\t~a~%" (task-name t) (task-desc t)))
                     tasks)
           0))

   ;; ── Common flows
   (task 'all "TOC → tangle → ensure Guix dirs"
         (lambda () (sh "make all")))
   (task 'stow "Safe stow (backs up real files, then stows)"
         (lambda () (sh "make safe-stow")))
   (task 'profiles "Build core+dev profiles (after tangling)"
         (lambda () (sh "make guix-core guix-dev")))
   (task 'guix-core "Build core profile from core.scm (uses substitutes)"
         (lambda () (sh "make guix-core")))
   (task 'guix-pull "guix pull (channel update)"
         (lambda () (sh "make guix-pull")))
   (task 'bridge "Apply Flatpak fonts/cursors bridge"
         (lambda () (sh "make bridge-flatpak")))
   (task 'x11-apply "Re-stow think/.xsessionrc & friends"
         (lambda () (sh "make x11-apply")))

   ;; ── Diagnostics / health
   (task 'health "Show registrar, GTK module, and nvim path"
         (lambda ()
           (sh "pgrep -af appmenu-registrar || echo 'registrar: (none)'")
           (sh "printf 'GTK_MODULES=%s\\n' \"${GTK_MODULES:-}\"")
           (with-core (lambda () "command -v nvim; nvim --version | sed -n '1,2p'"))
           0))

   ;; ── Capsule example: open Inkscape from a past Guix generation interactively
   (task 'inkscape-timecapsule "Run Inkscape from a chosen past Guix generation"
         (lambda ()
           (sh "guix describe --generations; echo 'Usage: guix time-machine --generation=N -- shell --pure inkscape -- inkscape'")
           0))
   ))

(define (run name . rest)
  (let ((t (find (lambda (t) (eq? (task-name t) name)) tasks)))
    (if t
        ((task-thunk t))
        (begin
          (format #t "Unknown task: ~a\n" name)
          1))))

(define (main args)
  (match args
    ((_ _ "list")   (run 'list))
    ((_ _ cmd)      (run (string->symbol cmd)))
    (_              (begin
                      (format #t "Usage: loom <task>\nTry: loom list\n")
                      1))))
;; Maak control plane (Scheme, XDG-friendly):1 ends here
