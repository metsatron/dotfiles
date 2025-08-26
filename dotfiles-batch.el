;;; dotfiles-batch.el --- Batch helpers for literate dotfiles  -*- lexical-binding: t -*-
(require 'cl-lib)
(require 'org)
(require 'ob-tangle)
(require 'ox)
(ignore-errors (require 'toc-org))       ;; optional
(ignore-errors (require 'org-make-toc))  ;; optional

(defun dotfiles--org-files (root)
  "Return a list of .org files under ROOT (repo)."
  (let ((default-directory root))
    (cl-remove-if
     (lambda (f)
       (or (string-match-p "/\\.git/" f)
           (string-match-p "\\.\\(html\\|md\\)$" f)))
     (directory-files-recursively root "\\.org\\'"))))

(defun org-dblock-write:dotfiles-index (params)
  "Populate a bullet list of Org files as links.
Params: :dir, :glob, :exclude, :recursive"
  (let* ((dir (expand-file-name (or (plist-get params :dir) default-directory)))
         (glob (or (plist-get params :glob) "*.org"))
         (recursive (plist-get params :recursive))
         (exclude-str (or (plist-get params :exclude) ""))
         (exclude (split-string exclude-str "[ ,]+" t))
         (files (if recursive
                    (directory-files-recursively dir (wildcard-to-regexp glob))
                  (directory-files dir nil glob t))))
    (setq files (cl-remove-if
                 (lambda (f)
                   (let ((bn (file-name-nondirectory f)))
                     (or (member bn exclude)
                         (string-match-p "/\\.git/" (expand-file-name f)))))
                 (if recursive files
                   (mapcar (lambda (f) (expand-file-name f dir)) files))))
    (let ((orig (point)))
      (insert (mapconcat
               (lambda (f)
                 (let* ((bn (file-name-nondirectory f))
                        (title (file-name-sans-extension bn)))
                   (format "- [[file:%s][%s]]" (file-relative-name f dir) title)))
               files
               "\n"))
      (when (= orig (point))
        (insert "- (no matching files)\n")))))

(defun dotfiles-batch-update (root)
  "Update dynamic blocks (incl. TOC) for all Org files under ROOT."
  (interactive "DRoot: ")
  (dolist (f (dotfiles--org-files root))
    (with-current-buffer (find-file-noselect f)
      (org-mode)
      (condition-case _ (org-update-all-dblocks) (error nil))
      (save-buffer)
      (kill-buffer))))

(defun dotfiles-batch-tangle (root)
  "Tangle all Org files under ROOT with confirmation disabled."
  (interactive "DRoot: ")
  (let ((org-confirm-babel-evaluate nil))
    (dolist (f (dotfiles--org-files root))
      (with-current-buffer (find-file-noselect f)
        (org-mode)
        (org-babel-tangle)
        (kill-buffer)))))

(provide 'dotfiles-batch)
;;; dotfiles-batch.el ends here
