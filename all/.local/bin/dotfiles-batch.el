;;; dotfiles-batch.el --- Batch helpers for literate dotfiles (root-only) -*- lexical-binding: t -*-

(require 'cl-lib)
(require 'org)
(require 'ob-tangle)
(require 'ox)

;; at top of all/.local/bin/dotfiles-batch.el
(when noninteractive
  (setq create-lockfiles nil
        make-backup-files nil
        auto-save-default nil
        backup-inhibited t
        vc-make-backup-files nil))

;; Batch safety: no backups, no autosave, no lockfiles
(setq make-backup-files nil
      backup-inhibited t
      auto-save-default nil
      create-lockfiles nil
      vc-follow-symlinks t)

;;; --- LainCore bootstrap for batch tangling ---
(require 'cl-lib)

;; Defaults (edit here or via the Org “Activation” block later)
(defvar lc/ui 'adobe-cc-dark-blue)
(defvar lc/syntax 'adobe-cc-dark-blue)
(defvar lc/overrides nil)

;; UI palettes
(defvar lc/palettes
  '((adobe-cc-dark-blue
     :white "#ffffff" :lighter "#5b5b5b" :base "#454545" :darker "#303030" :black "#000000"
     :accent "#4b6983")
    (chatgpt-dark-purple
     :white "#ffffff" :lighter "#414141" :base "#303030" :darker "#212121" :black "#0d0d0d"
     :accent "#6b3ab4")
    (obsidian-gray
     :white "#ECECEC" :lighter "#363636" :base "#1e1e1e" :darker "#262626" :black "#000000"
     :accent "#8CCEFF")
    (grok-dark
     :white "#e6e6e6" :lighter "#1b1d22" :base "#0f1115" :darker "#0b0d11" :black "#000000"
     :accent "#7c44ff")
    (claude-dark
     :white "#e8eaed" :lighter "#1e1f22" :base "#111214" :darker "#0b0c0d" :black "#000000"
     :accent "#6b9cff")))

(defun lc/p (theme key) (plist-get (alist-get theme lc/palettes) key))

;; Syntax palettes
(defvar lc/syntax-palettes
  '((adobe-cc-dark-blue
     :bg "#1f1f1f" :fg "#dbdbdb" :ui-accent "#4b6983"
     :string "#98c379" :keyword "#c678dd" :type "#61afef" :func "#e5c07b"
     :comment "#7f848e" :const "#d19a66" :error "#e06c75")
    (chatgpt-dark-purple
     :bg "#212121" :fg "#e2e6ea" :ui-accent "#6b3ab4"
     :string "#98c379" :keyword "#bb86fc" :type "#82aaff" :func "#e5c07b"
     :comment "#9aa3ab" :const "#d19a66" :error "#e06c75")
    (obsidian-gray
     :bg "#1e1e1e" :fg "#ECECEC" :ui-accent "#8CCEFF"
     :string "#C8F6A3" :keyword "#FFA870" :type "#9DE6FF" :func "#9BB8FF"
     :comment "#9EA4AA" :const "#FFD0AA" :error "#FF6E6E")
    (grok-dark
     :bg "#0f1115" :fg "#e6e6e6" :ui-accent "#7c44ff"
     :string "#b6f09c" :keyword "#b085ff" :type "#89b4ff" :func "#ffd28d"
     :comment "#a3a3a3" :const "#e8b882" :error "#ff6b6b")
    (claude-dark
     :bg "#111214" :fg "#e8eaed" :ui-accent "#6b9cff"
     :string "#97d59a" :keyword "#b58cff" :type "#6b9cff" :func "#ffd48a"
     :comment "#a0a4a8" :const "#d19a66" :error "#ff6b6b")))

(defun lc/s (theme key) (plist-get (alist-get theme lc/syntax-palettes) key))

(defun lc/get (app lane)
  (or (caddr (assoc app (cl-remove-if-not (lambda (x) (eq (cadr x) lane)) lc/overrides)))
      (pcase lane ('ui lc/ui) ('syntax lc/syntax))))

(defvar lc/fonts '(:ui "San Francisco Display 9" :mono "SFMono Nerd Font 10"))
(defun lc/font (lane) (plist-get lc/fonts lane))

(defun lc/emit (_app _lane path) path)
;;; --- end bootstrap ---

;; ---- root-only org list ----------------------------------------------------
(defun dotfiles--root-org-files (root)
  "Return only ROOT/*.org (no recursion, ignore dotfiles and exports)."
  (let* ((abs-root (file-name-as-directory (expand-file-name root)))
         (files (directory-files abs-root t "\\.org\\'")))
    (cl-remove-if
     (lambda (f)
       (or (not (file-regular-p f))
           (string-match-p "/\\." (file-name-nondirectory f))  ; ignore hidden names
           (string-match-p "\\.\\(html\\|md\\)\\'" f)))
     files)))

;; ---- dynamic block: list root org files ------------------------------------
(defun org-dblock-write:dotfiles-index (params)
  "Bullet list of ROOT/*.org as links. Params: :dir, :glob, :exclude"
  (let* ((dir (file-name-as-directory
               (expand-file-name (or (plist-get params :dir) default-directory))))
         (glob (or (plist-get params :glob) "*.org"))
         (exclude-str (or (plist-get params :exclude) ""))
         (exclude (split-string exclude-str "[ ,]+" t))
         (files (directory-files dir t (wildcard-to-regexp glob) t)))
    (setq files (cl-remove-if
                 (lambda (f)
                   (let ((bn (file-name-nondirectory f)))
                     (or (member bn exclude)
                         (not (file-regular-p f))
                         (string-match-p "/\\." bn))))
                 files))
    (let ((orig (point)))
      (insert (mapconcat
               (lambda (f)
                 (format "- [[file:%s][%s]]"
                         (file-relative-name f dir)
                         (file-name-sans-extension (file-name-nondirectory f))))
               files "\n"))
      (when (= orig (point)) (insert "- (no matching files)\n")))))

;; ---- batch entrypoints ------------------------------------------------------
(defun dotfiles-batch-update (root)
  "Update dynamic blocks for ROOT/*.org only."
  (interactive "DRoot: ")
  (dolist (f (dotfiles--root-org-files root))
    (with-current-buffer (find-file-noselect f)
      (org-mode)
      (condition-case _ (org-update-all-dblocks) (error nil))
      (save-buffer)
      (kill-buffer))))

(defun dotfiles-batch-tangle (root)
  "Tangle ROOT/*.org only, confirmation disabled."
  (interactive "DRoot: ")
  (let ((org-confirm-babel-evaluate nil))
    (dolist (f (dotfiles--root-org-files root))
      (with-current-buffer (find-file-noselect f)
        (org-mode)
        (org-babel-tangle)
        (kill-buffer)))))

(provide 'dotfiles-batch)
;;; dotfiles-batch.el ends here
