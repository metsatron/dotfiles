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
  "Populate a bullet list of Org files as links with #+DESCRIPTION.
Params: :dir, :glob, :exclude, :recursive"
  (let* ((dir (file-name-as-directory
               (expand-file-name (or (plist-get params :dir) default-directory))))
         (glob (or (plist-get params :glob) "*.org"))
         (recursive (plist-get params :recursive))
         (exclude-str (or (plist-get params :exclude) ""))
         (exclude (split-string exclude-str "[ ,]+" t))
         (files (if recursive
                    (directory-files-recursively dir (wildcard-to-regexp glob))
                  (directory-files dir t (wildcard-to-regexp glob) t))))
    (setq files (cl-remove-if
                 (lambda (f)
                   (let ((bn (file-name-nondirectory f)))
                     (or (member bn exclude)
                         (not (file-regular-p f))
                         (string-prefix-p "." bn)
                         (string-match-p "/\\.git/" f))))
                 files))
    (setq files (sort files #'string<))
    (let ((orig (point)))
      (insert (mapconcat
               (lambda (f)
                 (let* ((name (file-name-sans-extension (file-name-nondirectory f)))
                        (rel  (file-relative-name f dir))
                        (desc (with-temp-buffer
                                (insert-file-contents f nil 0 1024)
                                (goto-char (point-min))
                                (if (re-search-forward
                                     "^#\\+DESCRIPTION:[ \t]+\\(.+\\)" nil t)
                                    (match-string 1)
                                  nil))))
                   (if desc
                       (format "- [[file:%s][%s]] -- %s" rel name desc)
                     (format "- [[file:%s][%s]]" rel name))))
               files "\n"))
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
