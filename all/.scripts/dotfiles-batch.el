;;; dotfiles-batch.el --- Batch helpers for literate dotfiles  -*- lexical-binding: t -*-

(require 'cl-lib)
(require 'org)
(require 'ob)
(require 'ob-tangle)
(require 'ox)
(ignore-errors (require 'ox-md))
(ignore-errors (require 'ox-html))
(ignore-errors (require 'toc-org))
(ignore-errors (require 'org-make-toc))

(defun dotfiles--org-files (root)
  "Return a list of .org files under ROOT, ignoring .git/backups/json.data/docs/."
  (let ((default-directory root)
        (rx-ignore (rx "/" (or ".git" "backups" "json.data") "/")))
    (cl-remove-if (lambda (f) (string-match-p rx-ignore f))
                  (directory-files-recursively root "\\.org\\'"))))

(defun dotfiles--with-file (file &rest body)
  "Open FILE, run BODY, save and kill the buffer."
  (with-current-buffer (find-file-noselect file)
    (org-mode)
    (org-redisplay-inline-images)
    (condition-case _ (org-update-all-dblocks) (error nil))
    (prog1 (progn ,@body) (save-buffer) (kill-buffer))))

(defun dotfiles-batch-update (root)
  "Update dynamic blocks (incl. TOC) in all org files under ROOT."
  (interactive "DRoot: ")
  (dolist (f (dotfiles--org-files root))
    (dotfiles--with-file f
      (message "Updated TOC/dblocks: %s" f))))

(defun dotfiles-batch-tangle (root)
  "Tangle all org files under ROOT."
  (interactive "DRoot: ")
  (let ((org-confirm-babel-evaluate nil))
    (dolist (f (dotfiles--org-files root))
      (dotfiles--with-file f
        (org-babel-tangle)
        (message "Tangled: %s" f)))))

(defun dotfiles-batch-export (root kind)
  "Export all org files under ROOT to KIND: 'html or 'md."
  (interactive "DRoot: \nsKind (html|md): ")
  (dolist (f (dotfiles--org-files root))
    (dotfiles--with-file f
      (pcase kind
        ((or "html" 'html) (org-export-to-file 'html (concat (file-name-sans-extension f) ".html")))
        ((or "md" 'md)     (org-export-to-file 'md   (concat (file-name-sans-extension f) ".md")))))))

(provide 'dotfiles-batch)
;;; dotfiles-batch.el ends here
