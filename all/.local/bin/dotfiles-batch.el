;; [[file:../../../loom.org::*Maak control plane (Scheme, XDG-friendly)][Maak control plane (Scheme, XDG-friendly):2]]
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

;; Disable tangle comment fences by default for common langs we emit
(defun lc/set-comments-no (&rest langs)
  (dolist (L langs)
    (let* ((var (intern (format "org-babel-default-header-args:%s" L)))
           (alist (when (boundp var) (symbol-value var))))
      (set var (cons (cons :comments "no")
                     (assq-delete-all :comments (or alist '())))))))
(lc/set-comments-no 'yaml 'json 'css 'lua 'python 'sh 'bash 'emacs-lisp)

;;; --- LainCore bootstrap for batch tangling ---
(require 'cl-lib)

;;; --- Laincore bootstrap for dynamic :tangle headers ------------------------

(defun lc/batch-boot-if-needed (&optional root)
  (let* ((root (file-name-as-directory (or root default-directory)))
         (style (expand-file-name "style.org" root))
         (auto  (expand-file-name "all/.local/bin/laincore-autoload.el" root)))
    ;; non-fatal autoload — defines stubs like lc/emit if real boot fails
    (when (file-readable-p auto) (load auto t t))
    (when (and (not (fboundp 'lc/emit))
               (file-readable-p style))
      (require 'org) (require 'ob-emacs-lisp)
      (let ((org-confirm-babel-evaluate nil))
        (with-current-buffer (find-file-noselect style)
          (save-excursion
            (condition-case _ (progn
                                (org-babel-goto-named-src-block "lc-bootstrap")
                                (org-babel-execute-src-block))
              (error nil))
            (condition-case _ (progn
                                (org-babel-goto-named-src-block "lc-activate")
                                (org-babel-execute-src-block))
              (error nil))))))))

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
  "Tangle ROOT/*.org only; if FILE==style.org also run the emitter blocks."
  (interactive "DRoot: ")
  (setq root (file-name-as-directory (expand-file-name root)))
  ;; make lc/* available for dynamic :tangle, then tangle
  (lc/batch-boot-if-needed root)
  (let ((org-confirm-babel-evaluate nil))
    (dolist (f (dotfiles--root-org-files root))
      (message ">> TANGLE %s" f)
      (with-current-buffer (find-file-noselect f)
        (org-mode)
        (org-babel-tangle)
        ;; ALSO run “:tangle no” emitters for style.org
        (when (string= (file-name-nondirectory f) "style.org")
          (dolist (blk '("lc-bootstrap" "lc-activate"
                         "emit-gtk3-settings-ini" "emit-gtk3-css"
                         "emit-xfce4-terminal-theme" "emit-doom-base16-theme"
                         "emit-wezterm-flatpak" "emit-vscodium-theme"
                         "emit-emacs-vterm-ansi"))
            (condition-case _ (progn
                                (org-babel-goto-named-src-block blk)
                                (org-babel-execute-src-block))
              (error nil))))
        (kill-buffer)))))

(provide 'dotfiles-batch)
;;; dotfiles-batch.el ends here
;; Maak control plane (Scheme, XDG-friendly):2 ends here
