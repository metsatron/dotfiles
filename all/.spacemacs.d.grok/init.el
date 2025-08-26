;; -*- mode: emacs-lisp -*-
(defun dotspacemacs/layers ()
  "Configuration Layers declaration."
  (setq-default
   dotspacemacs-distribution 'spacemacs
   dotspacemacs-configuration-layer-path '()
   dotspacemacs-configuration-layers
   '(auto-completion
     better-defaults
     colors
     haskell
     helm
     html
     javascript
     latex
     pdf
     python
     shell
     spell-checking
     syntax-checking
     theming
     git
     version-control
     emacs-lisp
     org
     evil-commentary
     (brzeemacs :location (recipe :local "~/.emacs.d/private/brzeemacs"))
     (doom-themes :variables doom-themes-enable-bold t doom-themes-enable-italic t)
     (org :variables org-enable-github-support t)
     (shell :variables shell-default-height 30 shell-default-position 'bottom)
     (colors :variables colors-enable-nyan-cat-progress-bar t)
     (latex :variables latex-enable-folding t)
     (spell-checking :variables spell-checking-enable-by-default nil)
     (markdown :variables markdown-live-preview-engine 'vmd)
     (keyboard-layout
      :variables
      ;; NEIO on the home row (n e i o = ← ↓ ↑ →)
      kl-layout 'colemak-neio-literal)
     json
     web-beautify
     prettier
     node)
   dotspacemacs-additional-packages '(vterm evil-collection treemacs treemacs-evil treemacs-projectile helm-swoop)
   dotspacemacs-excluded-packages '()
   dotspacemacs-delete-orphan-packages t))

(defun dotspacemacs/init ()
  "Initialization function."
  (setq-default
   dotspacemacs-elpa-https t
   dotspacemacs-elpa-timeout 5
   dotspacemacs-editing-style 'vim
   dotspacemacs-verbose-loading nil
   dotspacemacs-startup-banner 'official  ; Restored; if small, try "~/path/to/large-logo.png" instead
   dotspacemacs-startup-lists '((recents . 10) (projects . 7))
   dotspacemacs-themes '(doom-molokai doom-spacegrey nord doom-one)
   dotspacemacs-default-font '("DejaVu Sans Mono" :size 16 :weight normal :width normal :powerline-scale 1.3)
   dotspacemacs-leader-key "SPC"
   dotspacemacs-emacs-command-key "SPC"
   dotspacemacs-ex-command-key ":"
   dotspacemacs-emacs-leader-key "M-m"
   dotspacemacs-major-mode-leader-key ","
   dotspacemacs-major-mode-emacs-leader-key "C-M-m"
   dotspacemacs-maximized-at-startup t
   dotspacemacs-which-key-delay 0.4
   dotspacemacs-loading-progress-bar t
   dotspacemacs-line-numbers '(:relative nil :disabled-for-modes dired-mode pdf-view-mode org-mode)
   dotspacemacs-folding-method 'origami
   dotspacemacs-search-tools '("ag" "pt" "ack" "grep")
   dotspacemacs-cache-directory (expand-file-name ".cache.grok/" user-emacs-directory)))  ; Isolated cache

(defun dotspacemacs/user-init ()
  "Initialization for user code."
  (setq inhibit-cl-warning t) ;; Suppress cl warnings
  (with-no-warnings (require 'cl))
  (setq byte-compile-warnings '(not cl-functions obsolete))
  (add-hook 'go-mode-hook (lambda () (setq indent-tabs-mode t tab-width 3))))

(defun dotspacemacs/user-config ()
  "Configuration for user code."
  (setq spaceline-highlight-face-func 'spaceline-highlight-face-evil-state)
  (set-face-attribute 'spaceline-evil-emacs nil :background "#21b089" :foreground "#151515")
  (setq powerline-default-separator 'arrow)
  (spaceline-toggle-minor-modes-off)
  (spaceline-toggle-buffer-size-off)
  (spaceline-toggle-line-column-off)
  (add-hook 'prog-mode-hook 'turn-on-fci-mode)
  (add-hook 'text-mode-hook 'turn-on-fci-mode)
  (add-hook 'doc-view-mode-hook 'auto-revert-mode)
  (set-face-attribute 'font-lock-comment-face nil :slant 'italic)
  (set-face-attribute 'font-lock-keyword-face nil :weight 'bold)
  (when (member "Source Code Pro Nerd Font Bold" (font-family-list))
    (set-face-attribute 'mode-line nil :font "Source Code Pro Nerd Font Bold"))
  (setq browse-url-browser-function 'browse-url-generic
        browse-url-generic-program "/usr/bin/floorp")
  (setq org-startup-with-inline-images t)
  (org-babel-do-load-languages
   'org-babel-load-languages
   '((perl . t) (dot . t) (R . t) (gnuplot . t) (clojure . t) (lisp . t)
     (org . t) (calc . t) (js . t) (latex . t) (plantuml . t)
     (ruby . t) (shell . t) (python . t) (emacs-lisp . t) (ditaa . t) (awk . t)
     (octave . t) (sed . t) (sql . t) (sqlite . t)))
  (with-eval-after-load 'vterm
    (evil-collection-vterm-setup)
    (define-key vterm-mode-map (kbd "C-j") 'vterm-send-down)
    (define-key vterm-mode-map (kbd "C-k") 'vterm-send-up))
  (with-eval-after-load 'org
    (when (require 'helm-swoop nil t)
      (add-hook 'org-mode-hook
                (lambda ()
                  (evil-define-key 'normal org-mode-map (kbd ", s") 'helm-swoop)))))
  (when (require 'evil-collection nil t)
    (evil-collection-init))
  (recentf-mode 1)
  (setq recentf-max-saved-items 100)
  ;; Recent files: force rebuild/load
  (setq recentf-auto-cleanup 'never)
  (run-with-idle-timer 300 t #'recentf-save-list)
  (recentf-cleanup)
  (recentf-load-list)
  ;; Layout: display rules
  (setq display-buffer-alist
        '(("\\*Treemacs\\*"
           (display-buffer-in-side-window)
           (side . left)
           (slot . 0)
           (window-width . 35)
           (preserve-size . (t . nil)))
          ("\\*vterm\\*"
           (display-buffer-in-side-window)
           (side . left)
           (slot . 1)
           (window-height . 0.3)
           (preserve-size . (nil . t)))))
  ;; Delayed auto-open (waits for load)
  (run-with-idle-timer 1 nil
                       (lambda ()
                         (treemacs)
                         (vterm)
                         (select-window (window-in-direction 'right))
                         (balance-windows)))
  ;; Treemacs extras
  (with-eval-after-load 'treemacs
    (treemacs-follow-mode t)
    (treemacs-filewatch-mode t)
    (treemacs-git-mode 'deferred)
    (treemacs-load-theme "doom-colors")))

(custom-set-faces
 '(default ((t (:background "#1c2526" :foreground "#d3c6aa"))))
 '(fringe ((t (:background "#1c2526"))))
 '(region ((t (:background "#4f5b66" :foreground "#e0decf")))))
