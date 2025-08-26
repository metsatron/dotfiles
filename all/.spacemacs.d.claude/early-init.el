;; -*- lexical-binding: t; -*-
;; Run before packages load (Emacs 27+). Keep ELPA & cache inside the Claude profile.

(defconst metsatron-claude-cache
  (expand-file-name "~/.spacemacs.d.claude/.cache/"))

;; Ensure directories exist
(when (not (file-directory-p metsatron-claude-cache))
  (make-directory metsatron-claude-cache t))

;; Put ELPA here (pre-package-initialization)
(setq package-user-dir (expand-file-name "elpa" metsatron-claude-cache))

;; Some packages read this directly for cache (Spacemacs mirrors it later)
(setq spacemacs-cache-directory metsatron-claude-cache)

;; Speed up startup a touch
(setq gc-cons-threshold (* 64 1024 1024))

