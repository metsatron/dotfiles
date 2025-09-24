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
