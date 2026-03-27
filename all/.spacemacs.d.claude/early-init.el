;; -*- lexical-binding: t; -*-
;; Run before packages load (Emacs 27+). Keep ELPA & cache inside the Claude profile.

(defconst metsatron-claude-cache
  (expand-file-name "~/.spacemacs.d.claude/.cache/"))

(defconst metsatron-eln-cache
  (expand-file-name "~/.cache/emacs/eln-cache/"))

;; Ensure directories exist
(when (not (file-directory-p metsatron-claude-cache))
  (make-directory metsatron-claude-cache t))
(when (not (file-directory-p metsatron-eln-cache))
  (make-directory metsatron-eln-cache t))

;; Keep native-comp output out of ~/.emacs.d so repo-backed profiles stay clean.
(when (fboundp 'startup-redirect-eln-cache)
  (startup-redirect-eln-cache metsatron-eln-cache))
(when (boundp 'native-comp-eln-load-path)
  (setq native-comp-eln-load-path (list metsatron-eln-cache)))

;; Put ELPA here (pre-package-initialization)
(setq package-user-dir (expand-file-name "elpa" metsatron-claude-cache))

;; Some packages read this directly for cache (Spacemacs mirrors it later)
(setq spacemacs-cache-directory metsatron-claude-cache)

;; Speed up startup a touch
(setq gc-cons-threshold (* 64 1024 1024))

;; Prefer GUIX_PROFILE/bin inside Emacs so subprocesses (python3) are consistent.
(let ((gp (getenv "GUIX_PROFILE")))
  (when (and gp (file-directory-p (expand-file-name "bin" gp)))
    (let ((bin (expand-file-name "bin" gp)))
      (setenv "PATH" (concat bin path-separator (getenv "PATH")))
      (add-to-list 'exec-path bin))))

(with-eval-after-load 'treemacs
  (setq treemacs-python-executable (or (executable-find "python3") "python3")))
