;;; early-init.el -*- lexical-binding: t; -*-

;; The native GNUstep build does not include Tree-sitter.  Some shared Emacs
;; Lisp/site-start code still assumes this variable exists, so provide the
;; standard empty search path without changing builds that do have Tree-sitter.
(defvar treesit-extra-load-path nil)

;; Keep package.el from trying to initialize a second package universe before
;; Guix's profile-provided packages are visible.
(setq package-enable-at-startup nil
      gc-cons-threshold (* 64 1024 1024)
      read-process-output-max (* 1024 1024))

;; Native compilation and mutable package state belong to the sanctuary home,
;; never beside this generated init file.
(let ((cache (expand-file-name "~/.cache/emacs-classic/")))
  (make-directory cache t)
  (when (and (fboundp 'startup-redirect-eln-cache)
             (boundp 'native-comp-eln-load-path))
    (startup-redirect-eln-cache (expand-file-name "eln/" cache))))
