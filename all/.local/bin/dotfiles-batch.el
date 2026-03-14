;; [[file:../../../loom.org::*Maak control plane (Scheme, XDG-friendly)][Maak control plane (Scheme, XDG-friendly):2]]
;;; dotfiles-batch.el --- Batch helpers for literate dotfiles (root-only) -*- lexical-binding: t; -*-

(require 'cl-lib)
(require 'org)
(require 'ob-tangle)
(require 'ox)

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

;; Disable tangle comment fences by default for common langs we emit
(defun lc/set-comments-no (&rest langs)
  (dolist (L langs)
    (let* ((var (intern (format "org-babel-default-header-args:%s" L)))
           (alist (when (boundp var) (symbol-value var))))
      (set var (cons (cons :comments "no")
                     (assq-delete-all :comments (or alist '())))))))
(lc/set-comments-no 'yaml 'json 'css 'lua 'python 'sh 'bash 'emacs-lisp)

;; --- LainCore font plumbing - style.org is canonical ------------------------

(defvar lc/fonts nil
  "Primary font plist. Should be set in style.org or LainCore, not here.")

(defun lc/font (lane)
  "Return font value for LANE from lc/fonts, falling back only if unset.
LC/fonts is expected to be set by style.org - this file must not override it."
  (plist-get
   (or lc/fonts
       '(:ui "San Francisco Display 9"
         :mono "SFMono Nerd Font 10"))
   lane))

(defun lc/s (theme key) (plist-get (alist-get theme lc/syntax-palettes) key))

(defun lc/get (app lane)
  (or (caddr (assoc app (cl-remove-if-not (lambda (x) (eq (cadr x) lane)) lc/overrides)))
      (pcase lane ('ui lc/ui) ('syntax lc/syntax))))

(defun lc/emit (_app _lane path) path)

(defun lc/batch-boot-if-needed (&optional root)
  (let* ((root  (file-name-as-directory (or root default-directory)))
         (style (expand-file-name "style.org" root))
         (auto  (expand-file-name "all/.local/bin/laincore-autoload.el" root)))
    ;; Load lightweight autoloads (lc/emit stub, etc)
    (when (file-readable-p auto)
      (load auto t t))
    ;; Always bootstrap style if present: defines lc/fonts, lc/font, lc/b, lc/w, lc/get...
    (when (file-readable-p style)
      (require 'org)
      (require 'ob-emacs-lisp)
      (let ((org-confirm-babel-evaluate nil))
        (with-current-buffer (find-file-noselect style)
          (org-mode)
          (save-excursion
            (condition-case _
                (progn
                  (org-babel-goto-named-src-block "lc-bootstrap")
                  (org-babel-execute-src-block))
              (error nil))
            (condition-case _
                (progn
                  (org-babel-goto-named-src-block "lc-activate")
                  (org-babel-execute-src-block))
              (error nil))))))))

;; ---- root-only org list ----------------------------------------------------
(defun dotfiles-root-org-files (root)
  "Return only ROOT/*.org (no recursion, ignore dotfiles and exports)."
  (let* ((abs-root (file-name-as-directory (expand-file-name root)))
         (files (directory-files abs-root t "\\.org\\'")))
    (cl-remove-if
     (lambda (f)
       (or (not (file-regular-p f))
           (string-prefix-p "." (file-name-nondirectory f)) ; ignore dotfiles
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
                         (string-prefix-p "." bn))))
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
  (dolist (f (dotfiles-root-org-files root))
    (with-current-buffer (find-file-noselect f)
      (org-mode)
      (condition-case _ (org-update-all-dblocks) (error nil))
      (save-buffer)
      (kill-buffer))))

(defun dotfiles-batch-tangle (root)
  "Tangle ROOT/*.org only; for style.org delegate to `loom-style`."
  (interactive "DRoot: ")
  (setq root (file-name-as-directory (expand-file-name root)))
  ;; Make lc/* available for dynamic :tangle and inline eval
  (lc/batch-boot-if-needed root)
  (let ((org-confirm-babel-evaluate nil))
    (dolist (f (dotfiles-root-org-files root))
      (message ">> TANGLE %s" f)
      (with-current-buffer (find-file-noselect f)
        (org-mode)
        (if (string= (file-name-nondirectory f) "style.org")
            ;; Delegate completely to loom-style, which:
            ;; - runs lc-bootstrap + lc-activate
            ;; - tangles style.org
            ;; - runs all :tangle no emitters (GTK, xfce, Doom, WezTerm, Codium, etc)
            (condition-case _
                (progn
                  (org-babel-goto-named-src-block "loom-style")
                  (org-babel-execute-src-block))
              (error
               (message "loom-style failed in %s" f)))
          ;; Normal org files just tangle as-is
          (org-babel-tangle))
        (kill-buffer)))))

(provide 'dotfiles-batch)
;;; dotfiles-batch.el ends here
;; Maak control plane (Scheme, XDG-friendly):2 ends here
