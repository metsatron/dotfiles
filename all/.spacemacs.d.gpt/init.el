;; -*- mode: emacs-lisp; lexical-binding: t; -*-

(defun dotspacemacs/layers ()
  (setq-default
   dotspacemacs-distribution 'spacemacs
   dotspacemacs-configuration-layers
   '(helm
     neotree
     git
     syntax-checking
     spell-checking
     python html javascript latex pdf
     org emacs-lisp
     (keyboard-layout :variables kl-layout 'colemak-neio-literal)
     (brzeemacs :location (recipe :local "~/.emacs.d/private/brzeemacs")))
   ;; install these directly (no fragile layers required)
   dotspacemacs-additional-packages '(vterm helm-swoop)
   dotspacemacs-excluded-packages '()
   dotspacemacs-delete-orphan-packages t))

(defun dotspacemacs/init ()
  (setq-default
   dotspacemacs-startup-banner 'official      ;; we’ll swap to your crest if found (below)
   dotspacemacs-startup-buffer-responsive t   ;; centered home
   dotspacemacs-startup-lists '((recents . 25) (projects . 7))
   dotspacemacs-themes '(doom-molokai nord doom-one)
   dotspacemacs-default-font '("DejaVu Sans Mono for Powerline" :size 12 :weight normal :width normal :powerline-scale 1.2)
   dotspacemacs-editing-style 'vim
   dotspacemacs-verbose-loading nil
   dotspacemacs-loading-progress-bar t
   dotspacemacs-line-numbers '(:relative nil :disabled-for-modes pdf-view-mode org-mode)
   ;; isolate this profile’s cache completely
   dotspacemacs-cache-directory (expand-file-name ".cache.gpt/" user-emacs-directory)))

(defun dotspacemacs/user-init ()
  ;; sandboxed recentf (pre-create dir; load immediately so Home has data)
  (defconst la/gpt-cache (expand-file-name ".cache.gpt/" user-emacs-directory))
  (make-directory la/gpt-cache t)
  (setq recentf-save-file (expand-file-name "recentf" la/gpt-cache)
        recentf-max-saved-items 200
        recentf-auto-cleanup 'never)
  (recentf-mode 1)
  (recentf-load-list))

(defun dotspacemacs/user-config ()
  ;; Use your crest if it exists
  (let ((crest (expand-file-name "~/.emacs.d/private/brzeemacs/img/brzeemacs.png")))
    (when (file-exists-p crest)
      (setq-default dotspacemacs-startup-banner crest)))

  ;; Small refresh so Recents render on Home after recentf loaded
  (add-hook 'emacs-startup-hook (lambda () (run-with-timer 0.3 nil #'spacemacs/home)))

  ;; Browser & org basics
  (setq browse-url-browser-function 'browse-url-generic
        browse-url-generic-program "/usr/bin/floorp"
        org-startup-with-inline-images t)
  (ignore-errors
    (org-babel-do-load-languages 'org-babel-load-languages
                                 '((shell . t) (python . t) (emacs-lisp . t))))

  ;; helm-swoop in org (only if present)
  (with-eval-after-load 'org
    (when (require 'helm-swoop nil t)
      (evil-define-key 'normal org-mode-map (kbd ", s") 'helm-swoop)))

  ;; Neotree: simple, reliable left tree
  (with-eval-after-load 'neotree
    (setq neo-window-width 28
          neo-smart-open t
          neo-theme (if (display-graphic-p) 'arrow 'arrow)))

  ;; Vterm keys (guarded); fallback to ansi-term if vterm isn’t ready yet
  (with-eval-after-load 'vterm
    (define-key vterm-mode-map (kbd "C-j") 'vterm-send-down)
    (define-key vterm-mode-map (kbd "C-k") 'vterm-send-up))

  ;; --- Workbench: Neotree left; two editors; terminal bottom-left of left editor ---
  (require 'seq nil 'noerror)
  (defun la/workbench ()
    "Neotree on the left; two editor panes; terminal on bottom-left (vterm if available)."
    (interactive)
    ;; 1) Show tree at left
    (neotree-show)
    ;; 2) Move to the editor to the right of neotree
    (other-window 1)
    ;; 3) Ensure a right editor pane
    (unless (window-in-direction 'right)
      (split-window-right))
    ;; 4) Split the LEFT editor horizontally and open a terminal below
    (let ((h (max 10 (/ (window-total-height) 2))))
      (split-window-below h)
      (other-window 1)
      (if (fboundp 'vterm)
          (vterm)
        (ansi-term "/bin/zsh"))
      (other-window -1))
    ;; 5) Balance
    (balance-windows-area))

  ;; Bind after core keymaps exist so which-key shows it and it always works
  (with-eval-after-load 'core-keybindings
    (spacemacs/declare-prefix "o" "own")
    (spacemacs/set-leader-keys "ow" #'la/workbench)

    ;; (optional) auto-open the workbench on startup in this sandbox
    ;; (add-hook 'emacs-startup-hook #'la/workbench)
    ))

