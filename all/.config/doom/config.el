;;; $DOOMDIR/config.el -*- lexical-binding: t; -*-

;; Place your private configuration here! Remember, you do not need to run 'doom
;; sync' after modifying this file!


;; Some functionality uses this to identify you, e.g. GPG configuration, email
;; clients, file templates and snippets. It is optional.
;; (setq user-full-name "John Doe"
;;       user-mail-address "john@doe.com")

;; Doom exposes five (optional) variables for controlling fonts in Doom:
;;
;; - `doom-font' -- the primary font to use
;; - `doom-variable-pitch-font' -- a non-monospace font (where applicable)
;; - `doom-big-font' -- used for `doom-big-font-mode'; use this for
;;   presentations or streaming.
;; - `doom-symbol-font' -- for symbols
;; - `doom-serif-font' -- for the `fixed-pitch-serif' face
;;
;; See 'C-h v doom-font' for documentation and more examples of what they
;; accept. For example:
;;
(setq doom-font (font-spec :family "JetBrainsMono Nerd Font" :size 12 :weight 'regular)
      doom-variable-pitch-font (font-spec :family "Fira Sans" :size 13))
;;
;; If you or Emacs can't find your font, use 'M-x describe-font' to look them
;; up, `M-x eval-region' to execute elisp code, and 'M-x doom/reload-font' to
;; refresh your font settings. If Emacs still can't find your font, it likely
;; wasn't installed correctly. Font issues are rarely Doom issues!

;; There are two ways to load a theme. Both assume the theme is installed and
;; available. You can either set `doom-theme' or manually load a theme with the
;; `load-theme' function. This is the default:
;;; --- Doom theme with fallback chain ---
(let* ((avail (custom-available-themes))
       (pick  (cond ((memq 'doom-sourcerer avail) 'doom-sourcerer)
                    ((memq 'doom-old-hope  avail) 'doom-old-hope)
                    (t 'doom-one))))
  (setq doom-theme pick))

;; This determines the style of line numbers in effect. If set to `nil', line
;; numbers are disabled. For relative line numbers, set this to `relative'.
(setq display-line-numbers-type t)

;; If you use `org' and don't want your org files in the default location below,
;; change `org-directory'. It must be set before org loads!
(setq org-directory "~/org/")


;; Whenever you reconfigure a package, make sure to wrap your config in an
;; `after!' block, otherwise Doom's defaults may override your settings. E.g.
;;
;;   (after! PACKAGE
;;     (setq x y))
;;
;; The exceptions to this rule:
;;
;;   - Setting file/directory variables (like `org-directory')
;;   - Setting variables which explicitly tell you to set them before their
;;     package is loaded (see 'C-h v VARIABLE' to look up their documentation).
;;   - Setting doom variables (which start with 'doom-' or '+').
;;
;; Here are some additional functions/macros that will help you configure Doom.
;;
;; - `load!' for loading external *.el files relative to this one
;; - `use-package!' for configuring packages
;; - `after!' for running code after a package has loaded
;; - `add-load-path!' for adding directories to the `load-path', relative to
;;   this file. Emacs searches the `load-path' when you load packages with
;;   `require' or `use-package'.
;; - `map!' for binding new keys
;;
;; To get information about any of these functions/macros, move the cursor over
;; the highlighted symbol at press 'K' (non-evil users must press 'C-c c k').
;; This will open documentation for it, including demos of how they are used.
;; Alternatively, use `C-h o' to look up a symbol (functions, variables, faces,
;; etc).
;;
;; You can also try 'gd' (or 'C-c c d') to jump to their definition and see how
;; they are implemented.

;; Start a unique server for Doom
(require 'server)
(unless (server-running-p) (server-start))

;; Keep backups & auto-saves out of the way
(setq backup-directory-alist '(("." . "~/.cache/emacs/backups/"))
      auto-save-file-name-transforms '((".*" "~/.cache/emacs/auto-saves/" t)))

;;; --- Always start maximized ---
(add-to-list 'initial-frame-alist '(fullscreen . maximized))
(add-to-list 'default-frame-alist '(fullscreen . maximized))

;;; --- If starting inside ~/RetroPie/isos/ports, open README.org on first frame ---
(defun la/ports-open-readme-on-start ()
  (when (and default-directory
             (string= (expand-file-name default-directory)
                      (expand-file-name "~/RetroPie/isos/ports/"))
             (file-exists-p "README.org"))
    (find-file "README.org")))
(add-hook 'window-setup-hook #'la/ports-open-readme-on-start)

;;; --- Org Babel: only what we need (shell + elisp) ---
(after! org
  (org-babel-do-load-languages
   'org-babel-load-languages
   '((emacs-lisp . t)
     (shell . t))))

(after! projectile
  (add-to-list 'projectile-project-search-path "~/RetroPie/isos/ports/"))

(after! org
  (add-to-list 'org-capture-templates
               '("p" "Ports launcher" plain
                 (file+headline "~/RetroPie/isos/ports/README.org" "Inbox")
                 "* %?\n#+begin_src sh :tangle ./bin/%(read-string \"script name: \").sh\nset -euo pipefail\nROOT=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\"/.. && pwd)\"\n#+end_src\n"
                 :jump-to-captured t)))

;;; --- Colemak NEIO literal motions (normal state) ---
(after! evil
  ;; cursor movement (visual-line aware)
  (map! :n "n" #'evil-backward-char
        :n "e" #'evil-next-visual-line
        :n "i" #'evil-previous-visual-line
        :n "o" #'evil-forward-char)

  ;; preserve search-next/prev on Meta bindings
  (map! :n "M-n" #'evil-ex-search-next
        :n "M-N" #'evil-ex-search-previous)

  ;; window navigation with C-w + NEIO
  (define-key evil-window-map (kbd "n") #'evil-window-left)
  (define-key evil-window-map (kbd "e") #'evil-window-down)
  (define-key evil-window-map (kbd "i") #'evil-window-up)
  (define-key evil-window-map (kbd "o") #'evil-window-right))

;;; --- Treemacs NEIO (collapse/expand + move) ---
(after! treemacs
  (evil-define-key 'normal treemacs-mode-map
    (kbd "i") #'treemacs-previous-line
    (kbd "e") #'treemacs-next-line
    (kbd "o") #'treemacs-TAB-action          ;; toggle node (open/close)
    (kbd "n") #'treemacs-collapse-parent-node
    (kbd "RET") #'treemacs-RET-action))

;;; --- Dired NEIO (up dir / open / move) ---
(after! dired
  (evil-define-key 'normal dired-mode-map
    (kbd "i") #'dired-previous-line
    (kbd "e") #'dired-next-line
    (kbd "o") #'dired-find-file
    (kbd "n") #'dired-up-directory))

(defun la/next-tab () (interactive)
  (cond ((bound-and-true-p centaur-tabs-mode) (call-interactively 'centaur-tabs-forward))
        ((bound-and-true-p tab-bar-mode)      (call-interactively 'tab-bar-switch-to-next-tab))
        ((fboundp '+workspace/switch-next)    (+workspace/switch-next))
        (t (other-window 1))))

(defun la/prev-tab () (interactive)
  (cond ((bound-and-true-p centaur-tabs-mode) (call-interactively 'centaur-tabs-backward))
        ((bound-and-true-p tab-bar-mode)      (call-interactively 'tab-bar-switch-to-prev-tab))
        ((fboundp '+workspace/switch-previous) (+workspace/switch-previous))
        (t (other-window -1))))

(defun la/close-tab () (interactive)
  (cond ((bound-and-true-p centaur-tabs-mode) (call-interactively 'centaur-tabs-close-current-tab))
        ((bound-and-true-p tab-bar-mode)      (call-interactively 'tab-bar-close-tab))
        ((fboundp '+workspace/delete)         (+workspace/delete))
        (t (kill-current-buffer))))

(map! :g "C-<next>"  #'la/next-tab
      :g "C-<prior>" #'la/prev-tab
      :g "C-S-w"     #'la/close-tab)

(defun la/workbench ()
  (interactive)
  (let ((buf (current-buffer)))
    (delete-other-windows)
    (split-window-right)
    (other-window 1)
    (when (fboundp #'treemacs) (treemacs) (other-window 1))
    (switch-to-buffer buf)))
(map! :leader :desc "Workbench" "o w" #'la/workbench)
