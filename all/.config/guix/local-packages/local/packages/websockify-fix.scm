

;; The =websockify= 0.11.0-1 local variant — Guix main's own package, unchanged except
;; for one missing test input. At the fleet pin its =check= phase dies importing
;; =tests/test_token_plugins.py=: =python-jwcrypto= 1.5.6 imports =typing_extensions=
;; without propagating it (=ModuleNotFoundError=, build log on kikin-kushi 2026-10-01).
;; Adding =python-typing-extensions= as a native input lets upstream's full suite run
;; instead of skipping it. Retire this variant once Guix main builds cleanly.


;; [[file:../../../../../../package-guix.org::*Guix User profile manifests][Guix User profile manifests:4]]
;;; Local Guix package — websockify 0.11.0 with the missing test input restored.
;;; Why local: Guix main's websockify fails its check phase at the fleet pin
;;; (python-jwcrypto needs typing_extensions, which it does not propagate).

(define-module (local packages websockify-fix)
  #:use-module (guix packages)
  #:use-module (gnu packages python-build)
  #:use-module (gnu packages web))

(define-public websockify-fix
  (package
    (inherit websockify)
    (version "0.11.0-1")
    (native-inputs
     (modify-inputs (package-native-inputs websockify)
       (append python-typing-extensions)))))
;; Guix User profile manifests:4 ends here
