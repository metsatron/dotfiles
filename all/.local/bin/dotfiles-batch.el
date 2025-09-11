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
