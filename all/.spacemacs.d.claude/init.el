;; -*- lexical-binding: t; -*-

(defun dotspacemacs/layers ()
  (setq-default
   dotspacemacs-distribution 'spacemacs
   dotspacemacs-enable-lazy-installation 'unused
   dotspacemacs-ask-for-lazy-installation t
   dotspacemacs-configuration-layer-path '()
   dotspacemacs-additional-packages '(mixed-pitch org-appear)

   dotspacemacs-configuration-layers
   '(
     ;; Core / UI
     helm
     auto-completion
     better-defaults
     git
     treemacs
     syntax-checking
     spell-checking
     ;; (brzeemacs :location (recipe :local "~/.emacs.d/private/brzeemacs"))
     ;; Languages
     emacs-lisp
     python
     html
     javascript
     latex
     markdown
     org
     spacemacs-layouts

     ;; Your canonical keyboard layout
     (keyboard-layout :variables kl-layout 'colemak-neio-literal)

     ;; Shell integration (we'll use vterm as the shell)
     (shell :variables
            shell-default-shell 'vterm
            shell-default-height 10
            shell-default-position 'bottom)
     )

   ;; Keep vterm as a package (no vterm *layer* on your Spacemacs branch)
   dotspacemacs-additional-packages '(vterm doom-themes centaur-tabs)
   dotspacemacs-frozen-packages '()
   dotspacemacs-excluded-packages '()
   dotspacemacs-install-packages 'used-only))

(defun dotspacemacs/init ()
  (setq dotspacemacs-filepath  (expand-file-name "~/.spacemacs.d.claude/init.el")
        dotspacemacs-directory (file-name-directory dotspacemacs-filepath))

  (setq-default
   ;; Try to keep caches scoped; we also set this in early-init for packages that use it directly
   dotspacemacs-cache-directory (expand-file-name "~/.spacemacs.d.claude/.cache/")
   ;; Themes kept simple to avoid first-boot theme issues
   dotspacemacs-themes '(doom-Iosvkem doom-tomorrow-night doom-opera doom-molokai doom-gruvbox doom-dark+)
   (setq custom-safe-themes t)

   ;; ELPA behavior
   dotspacemacs-elpa-https t
   dotspacemacs-elpa-timeout 10
   dotspacemacs-elpa-subdirectory 'emacs-version
   dotspacemacs-check-for-update nil
   dotspacemacs-editing-style 'vim

   ;; Startup buffer with recents
   dotspacemacs-startup-buffer-show-version t
   dotspacemacs-startup-banner 'official
   dotspacemacs-startup-lists '((recents . 15) (projects . 7))
   dotspacemacs-startup-buffer-responsive t
   dotspacemacs-show-startup-list-numbers t

   ;; Use a font you *have*: SFMono (see your fc-list)
   dotspacemacs-default-font '("SFMono Nerd Font Mono" :size 11 :weight 'normal)

   ;; Leader keys
   dotspacemacs-leader-key "SPC"
   dotspacemacs-emacs-command-key "SPC"
   dotspacemacs-ex-command-key ":"
   dotspacemacs-emacs-leader-key "M-m"
   dotspacemacs-major-mode-leader-key ","
   dotspacemacs-major-mode-emacs-leader-key "C-M-m"

   ;; Ergonomics
   dotspacemacs-display-default-layout nil
   dotspacemacs-smooth-scrolling t
   dotspacemacs-line-numbers '(:relative nil :visual nil)
   dotspacemacs-folding-method 'evil
   dotspacemacs-search-tools '("rg" "ag" "pt" "ack" "grep")
   dotspacemacs-show-trailing-whitespace t
   dotspacemacs-whitespace-cleanup nil))

(defun dotspacemacs/user-env ()
  (spacemacs/load-spacemacs-env))

(defun dotspacemacs/user-init ()
  ;; ---- Cache / ELPA isolation (belts & braces) -------------------------
  (let* ((cache (expand-file-name "~/.spacemacs.d.claude/.cache/"))
         (elpa  (expand-file-name "elpa" cache))
         (cust  (expand-file-name "custom.el" (expand-file-name "~/.spacemacs.d.claude/"))))
    (unless (file-exists-p cache) (make-directory cache t))
    ;; Some packages consult these directly; force them here too
    (setq spacemacs-cache-directory cache
          package-user-dir          elpa
          custom-file               cust)
    ;; recentf scoped here
    (setq recentf-save-file (expand-file-name "recentf" cache)
          recentf-max-saved-items 200
          recentf-auto-cleanup 'never)
    (require 'recentf nil t)
    (when (fboundp 'recentf-mode) (recentf-mode 1)))

  ;; ---- Treemacs compat shim --------------------------------------------
  ;; Newer Treemacs dropped this internal var; Spacemacs/winum still refer to it.
  (unless (boundp 'treemacs--buffer-name-prefix)
    (defvar treemacs--buffer-name-prefix " *Treemacs-")))

(defun dotspacemacs/user-load () )

(defun dotspacemacs/user-config ()
  (with-eval-after-load 'files
    (add-to-list 'safe-local-eval-forms
                 '(progn (pp-buffer) (indent-buffer))))

  (defun metsatron/find-profile-init ()        (interactive) (find-file "~/.spacemacs.d.claude/init.el"))
  (defun metsatron/find-profile-early-init ()  (interactive) (find-file "~/.spacemacs.d.claude/early-init.el"))
  (defun metsatron/find-profile-env ()         (interactive) (find-file "~/.spacemacs.d.claude/.spacemacs.env"))

  (spacemacs/set-leader-keys
    "fed" #'metsatron/find-profile-init      ;; classic “dotfile”
    "fei" #'metsatron/find-profile-init
    "feI" #'metsatron/find-profile-early-init
    "fev" #'metsatron/find-profile-env)

  ;; ---------- Org look & feel (Obsidian-ish, theme-proof) ----------
  ;; Enforce fonts you already chose, everywhere (no size changes here)
  (defun metsatron/force-fonts (&optional frame)
    (with-selected-frame (or frame (selected-frame))
      ;; Default/UI & fixed-pitch = SFMono Nerd Font Mono @ 120/110 (your values)
      (set-face-attribute 'default      nil :family "SFMono Nerd Font Mono" :height 110 :weight 'normal)
      (set-face-attribute 'fixed-pitch  nil :family "SFMono Nerd Font Mono" :height 110 :weight 'normal)
      ;; Org body = San Francisco Display @ 120 (your value)
      (set-face-attribute 'variable-pitch nil :family "San Francisco Display" :height 120 :weight 'normal)
      ;; Make sure symbols/PUA don’t drag in weird fallbacks/sizes
      (set-fontset-font t 'symbol  (font-spec :family "Symbols Nerd Font Mono") nil 'prepend)
      (set-fontset-font t 'unicode (font-spec :family "Symbols Nerd Font Mono") nil 'append)
      (set-fontset-font t '(#xE000 . #xF8FF) (font-spec :family "Symbols Nerd Font Mono") nil 'prepend)))

  ;; Apply now + for all future frames
  (metsatron/force-fonts)
  (add-hook 'after-make-frame-functions #'metsatron/force-fonts)
  (add-hook 'server-after-make-frame-hook #'metsatron/force-fonts)

  (with-eval-after-load 'org
    ;; your existing org faces (keep as-is) …
    (setq org-hide-emphasis-markers t
          org-pretty-entities t
          org-ellipsis "…")

    ;; Hide stars by default (theme-proof)
    (defvar metsatron/org-stars-hidden t)

    (defvar metsatron/org--hide-stars-rule '(("^\\(\\*+\\) " (1 'org-hide))))
    (defun metsatron/org--apply-stars-visibility ()
      (if metsatron/org-stars-hidden
          (progn
            (setq org-hide-leading-stars t)
            (set-face-attribute 'org-hide nil
                                :foreground (face-background 'default nil t) :inherit nil)
            (font-lock-add-keywords nil metsatron/org--hide-stars-rule 'append))
        (setq org-hide-leading-stars nil)
        (font-lock-remove-keywords nil metsatron/org--hide-stars-rule)
        (set-face-attribute 'org-hide nil :foreground nil :inherit 'shadow))
      (font-lock-flush) (font-lock-ensure))

    ;; Headings: sizes (leave colors to theme unless you want to set them)
    (with-eval-after-load 'org
      (defun metsatron/org-apply-heading-faces ()
        ;; Title 23px, white, bold
        (set-face-attribute 'org-document-title nil
                            :inherit 'variable-pitch :weight 'bold
                            :foreground "#ffffff" :height 173)
        ;; Author: keep size, make white + bold
        (set-face-attribute 'org-document-info nil
                            :inherit 'variable-pitch :weight 'bold
                            :foreground "#ffffff")
        ;; H1/H2/H3 exact sizes; keep the Obsidian-clean look
        (set-face-attribute 'org-level-1 nil
                            :inherit 'variable-pitch :weight 'bold :height 158)
        (set-face-attribute 'org-level-2 nil
                            :inherit 'variable-pitch :weight 'bold :height 143)
        (set-face-attribute 'org-level-3 nil
                            :inherit 'variable-pitch :weight 'bold :height 120)
        ;; Below: keep slightly above body; tweak if you want
        (set-face-attribute 'org-level-4 nil
                            :inherit 'variable-pitch :weight 'bold :height 110)
        (dolist (lv '(org-level-5 org-level-6 org-level-7 org-level-8))
          (set-face-attribute lv nil :inherit 'variable-pitch :weight 'bold :height 110)))
      ;; ensure your existing metsatron/org-looks calls this
      )

    (defun metsatron/org-looks ()
      (variable-pitch-mode 1)
      ;; keep code/tables mono
      (dolist (f '(org-code org-verbatim org-table
                            org-block org-block-begin-line org-block-end-line
                            org-meta-line org-special-keyword org-checkbox))
        (set-face-attribute f nil :inherit 'fixed-pitch))
      (metsatron/org-apply-heading-faces)
      (metsatron/org--apply-stars-visibility))

    (add-hook 'org-mode-hook #'metsatron/org-looks)

    ;; Re-apply after theme switches
    (advice-add 'load-theme :after
                (lambda (&rest _)
                  (dolist (b (buffer-list))
                    (with-current-buffer b
                      (when (derived-mode-p 'org-mode)
                        (metsatron/org-looks))))))

    ;; One toggle to rule them all: stars + emphasis
    (defun metsatron/org-toggle-pretty ()
      (interactive)
      (setq org-hide-emphasis-markers (not org-hide-emphasis-markers))
      (setq metsatron/org-stars-hidden (not metsatron/org-stars-hidden))
      (metsatron/org--apply-stars-visibility))
    (define-key org-mode-map (kbd "C-c e") #'metsatron/org-toggle-pretty)
    (spacemacs/set-leader-keys "oe" #'metsatron/org-toggle-pretty))

  ;; --------------- Evil Colemak NEIO movement ----------------
  ;; Leader window moves: SPC w n/e/i/o
  (spacemacs/set-leader-keys
    "wn" 'evil-window-left
    "we" 'evil-window-down
    "wi" 'evil-window-up
    "wo" 'evil-window-right)

  ;; Also remap Evil’s C-w prefix to NEIO
  (with-eval-after-load 'evil
    (define-key evil-window-map "n" 'evil-window-left)
    (define-key evil-window-map "e" 'evil-window-down)
    (define-key evil-window-map "i" 'evil-window-up)
    (define-key evil-window-map "o" 'evil-window-right))

  ;; Make sure persp is on and state helpers are available
  (with-eval-after-load 'persp-mode
    (require 'persp-state nil t))

  (add-hook 'emacs-startup-hook
            (lambda ()
              (require 'persp-mode)
              (persp-mode 1)
              (require 'persp-state nil t)))

  ;; Ensure layouts are on
  (add-hook 'emacs-startup-hook
            (lambda ()
              (require 'persp-mode nil t)
              (when (featurep 'persp-mode) (persp-mode 1))
              (ignore-errors (require 'persp-state))))  ;; may or may not exist

  (defun metsatron/persp--save (file)
    (cond
     ((fboundp 'persp-state-save)           (persp-state-save file))
     ((fboundp 'persp-save-state-to-file)   (persp-save-state-to-file file))
     (t                                     ;; fallback
      (with-temp-file file
        (prin1 (list :type 'window-state :state (window-state-get nil t)) (current-buffer))))))

  (defun metsatron/persp--load (file)
    (cond
     ((fboundp 'persp-state-load)           (persp-state-load file))
     ((fboundp 'persp-load-state-from-file) (persp-load-state-from-file file))
     (t
      ;; fallback: window-state
      (let ((data (with-temp-buffer (insert-file-contents file) (read (current-buffer)))))
        (when (eq (plist-get data :type) 'window-state)
          ;; create a vterm up front if state references one
          (when (and (fboundp 'vterm)
                     (save-excursion (goto-char (point-min))
                                     (search-forward "\"*vterm*\"" nil t)))
            (ignore-errors (vterm)))
          ;; delete side windows so we can restore freely
          (let ((ignore-window-parameters t))
            (dolist (w (window-list))
              (when (window-parameter w 'window-side) (delete-window w))))
          (window-state-put (plist-get data :state) (frame-root-window) 'safe))))))

  (defun metsatron/persp-save-workbench ()
    (interactive)
    (metsatron/persp--save "~/.spacemacs.d.claude/workbench.state")
    (message "Workbench saved."))

  (defun metsatron/persp-load-workbench ()
    (interactive)
    (if (file-exists-p "~/.spacemacs.d.claude/workbench.state")
        (progn
          (metsatron/persp--load "~/.spacemacs.d.claude/workbench.state")
          (message "Workbench loaded."))
      (message "No workbench.state found.")))

  (spacemacs/declare-prefix "ol" "layout")
  (spacemacs/set-leader-keys
    "ols" #'metsatron/persp-save-workbench
    "oll" #'metsatron/persp-load-workbench)

  ;; Browser fallback
  (setq browse-url-browser-function 'browse-url-generic
        browse-url-generic-program (or (executable-find "floorp")))

  (with-eval-after-load 'doom-themes
    (setq doom-themes-enable-bold t
          doom-themes-enable-italic t))

  ;; Org basics
  (with-eval-after-load 'org
    (setq org-startup-with-inline-images t
          org-startup-indented t)
    (org-babel-do-load-languages
     'org-babel-load-languages
     '((shell . t) (python . t) (emacs-lisp . t))))

  ;; Treemacs sensible defaults (enable modes via functions)
  (with-eval-after-load 'treemacs
    (setq treemacs-width 20
          treemacs-is-never-other-window nil)
    (treemacs-follow-mode 1)
    (treemacs-filewatch-mode 1)
    (treemacs-git-mode 'deferred))

  (defun metsatron/treemacs-narrow ()
    (when (fboundp 'treemacs-set-width)
      (treemacs-set-width 20)))

  (with-eval-after-load 'treemacs
    (add-hook 'treemacs-mode-hook #'metsatron/treemacs-narrow)
    ;; optional: make PNG icons smaller to allow narrower width
    (ignore-errors (treemacs-resize-icons 16)))
  (with-eval-after-load 'doom-themes
    (add-hook 'treemacs-mode-hook #'metsatron/treemacs-narrow))

  ;; vterm comfort
  (with-eval-after-load 'vterm
    (define-key vterm-mode-map (kbd "C-q") #'vterm-send-next-key)
    (define-key vterm-mode-map (kbd "C-y") #'vterm-yank)
    (setq vterm-max-scrollback 10000))

  ;; --- Workbench layout (safe order: build splits before side window) ---
  (defun metsatron/setup-workbench ()
    "Right: two editor panes. Left: Treemacs side window.
    Left-top editor also gets a bottom split for vterm."
    (interactive)
    (delete-other-windows)
    ;; build editor grid first (no side windows yet)
    (let* ((left  (selected-window))
           (right (split-window-right)))
      (select-window left)
      (let* ((term (split-window-below)))      ; make the split first…
        (select-window term)
        (if (fboundp 'vterm) (vterm)
          (ansi-term (or (getenv "SHELL") "/bin/bash")))
        ;; …then clamp bottom-left height exactly to N lines
        (let ((desired 8))
          (window-resize term (- desired (window-total-height term)))))
      (select-window right))
    ;; now open treemacs as a side window
    (treemacs)
    ;; enforce treemacs width for this session too
    (when (fboundp 'treemacs-set-width) (treemacs-set-width 20)))

  ;; Better glyph coverage everywhere (including vterm)
  (setq inhibit-compacting-font-caches t)  ;; performance + fewer fallback glitches

  (let ((nf "Symbols Nerd Font Mono"))
    ;; Give Nerd Symbols highest priority for symbols & PUA codepoints
    (set-fontset-font t 'symbol  (font-spec :family nf) nil 'prepend)
    (set-fontset-font t 'unicode (font-spec :family nf) nil 'append)
    (set-fontset-font t '(#xE000 . #xF8FF) (font-spec :family nf) nil 'prepend))  ; Private Use Area

  ;; Emoji (if you have it)
  (when (member "Noto Color Emoji" (font-family-list))
    (set-fontset-font t 'emoji (font-spec :family "Noto Color Emoji") nil 'append))

  ;; Leader: SPC o w
  (spacemacs/declare-prefix "o" "open")
  (spacemacs/declare-prefix "ow" "workbench")
  (spacemacs/set-leader-keys "ow" #'metsatron/setup-workbench)

  ;; Fallback key
  (global-set-key (kbd "C-c w") #'metsatron/setup-workbench)

  ;; -------------------- Centaur Tabs (stable) --------------------
  (require 'centaur-tabs)
  (setq centaur-tabs-style "rounded"
        centaur-tabs-height 24
        centaur-tabs-set-icons nil
        centaur-tabs-set-close-button nil
        centaur-tabs-set-modified-marker t
        centaur-tabs-modified-marker "*"
        centaur-tabs-cycle-scope 'tabs
        centaur-tabs-show-new-tab-button nil
        centaur-tabs-show-navigation-buttons t
        centaur-tabs-group-by-projectile-project t)

  ;; Grouping (safe for special buffers)
  (setq centaur-tabs-group-by-projectile-project nil)  ;; we’ll use our own grouping

  (defun metsatron/ct-buffer-groups ()
    (list
     (cond
      ;; special/service
      ((or (string-prefix-p " *" (buffer-name))
           (member (buffer-name)
                   '("*spacemacs*" "*Messages*" "*Compile-Log*" "*Help*"
                     "*Warnings*" "*Backtrace*" "*Which Key*")))
       "Service")
      ;; tools
      ((memq major-mode '(treemacs-mode vterm-mode term-mode
                                        magit-status-mode magit-process-mode
                                        package-menu-mode))
       "Tools")
      ;; everything else = one big group
      ((buffer-file-name) "All")
      (t "Buffers"))))
  (setq centaur-tabs-buffer-groups-function #'metsatron/ct-buffer-groups)

  ;; make sure we’re cycling tabs, not groups
  (setq centaur-tabs-cycle-scope 'tabs)

  ;; force refresh
  (centaur-tabs-mode -1)
  (centaur-tabs-mode +1)

  ;; Hiding (correct signature: 1 arg = buffer)
  (with-eval-after-load 'centaur-tabs
    (setq centaur-tabs-hide-tab-function
          (lambda (&rest args)
            ;; Accept (BUFFER) or (NAME BUFFER)
            (let* ((buffer (if (= (length args) 1) (car args) (cadr args)))
                   (name   (if (= (length args) 1) (buffer-name buffer) (car args)))
                   (mode   (buffer-local-value 'major-mode buffer)))
              (or
               ;; names to hide
               (string-prefix-p " *Treemacs" name)
               (string-prefix-p "*helm" name)          ; *helm mini*, *helm M-x*, *Helm Find Files*
               (member name '("*Which Key*" "*spacemacs*" "*Messages*" "*scratch*" "*Completions*" "*info*"))
               ;; modes to hide (covers Info, Helm, Treemacs, etc.)
               (memq mode '(helm-major-mode spacemacs-buffer-mode which-key-mode
                                            treemacs-mode help-mode helpful-mode Info-mode))))))
    ;; Optional: don’t show a tab for the current layout name
    (setq centaur-tabs-show-navigation-buttons t))

  (with-eval-after-load 'centaur-tabs
    ;; A) generic excludes that all builds support
    (setq centaur-tabs-excluded-regexps
          '("^\\*helm" "^\\*scratch\\*$" "^\\*info\\*$"
            "^\\*Messages\\*$" "^\\*Which Key\\*$" "^ \\*Treemacs"))

    ;; B) hide function (handles 1-arg and 2-arg call sites)
    (setq centaur-tabs-hide-tab-function
          (lambda (&rest args)
            (let* ((buffer (if (= (length args) 1) (car args) (cadr args)))
                   (name   (if (= (length args) 1) (buffer-name buffer) (car args)))
                   (mode   (buffer-local-value 'major-mode buffer)))
              (or
               (string-prefix-p " *Treemacs" name)
               (string-prefix-p "*helm" name)
               (member name '("*Which Key*" "*spacemacs*" "*Messages*" "*scratch*" "*Completions*" "*info*"))
               (memq mode '(helm-major-mode spacemacs-buffer-mode which-key-mode
                                            treemacs-mode help-mode helpful-mode Info-mode))))))

    ;; Force the tabline to rebuild right now
    (centaur-tabs-mode -1)
    (centaur-tabs-mode +1))

  ;; Don't try to show tabs inside these modes
  (add-hook 'spacemacs-buffer-mode-hook #'centaur-tabs-local-mode)
  (add-hook 'treemacs-mode-hook         #'centaur-tabs-local-mode)

  ;; Enable
  (centaur-tabs-mode 1)

  ;; Firefox-like keys
  (global-set-key (kbd "C-t")         (lambda () (interactive)
                                        (switch-to-buffer (generate-new-buffer "*untitled*"))))
  (global-set-key (kbd "<C-prior>")   #'centaur-tabs-backward) ; Ctrl+PgUp
  (global-set-key (kbd "<C-next>")    #'centaur-tabs-forward)  ; Ctrl+PgDn
  (global-set-key (kbd "<C-S-prior>") #'centaur-tabs-move-current-tab-to-left)
  (global-set-key (kbd "<C-S-next>")  #'centaur-tabs-move-current-tab-to-right)
  (global-set-key (kbd "C-S-w")       #'kill-current-buffer)   ; avoid clobbering Evil's C-w

  ;; Reopen last closed file-tab (robust stack)
  (defvar metsatron/killed-file-stack nil)
  (add-hook 'kill-buffer-hook
            (lambda ()
              (when buffer-file-name
                (push buffer-file-name metsatron/killed-file-stack))))
  (defun metsatron/reopen-last-closed-tab ()
    (interactive)
    (let ((f (seq-find #'file-exists-p metsatron/killed-file-stack)))
      (if f (progn (find-file f)
                   (setq metsatron/killed-file-stack (delete f metsatron/killed-file-stack)))
        (message "No recently killed file buffer found."))))
  (global-set-key (kbd "C-S-t") #'metsatron/reopen-last-closed-tab)

  (defun metsatron/new-tab (&optional arg)
    "C-n: new tab. With C-u, prompt to open a file."
    (interactive "P")
    (if arg
        (call-interactively #'spacemacs/helm-find-files)
      (call-interactively #'spacemacs/new-empty-buffer)))

  (defun metsatron/go-home ()
    "C-t: go to the Spacemacs home buffer."
    (interactive)
    (spacemacs-buffer/goto-buffer))

  ;; Only in Evil normal/motion/visual (keep Insert/minibuffer defaults)
  (dolist (map (list evil-normal-state-map evil-motion-state-map evil-visual-state-map))
    (define-key map (kbd "C-n") #'metsatron/new-tab)
    (define-key map (kbd "C-t") #'metsatron/go-home))

  ;; Keep Evil's window prefix; bind close-tab to C-S-w (GUI usually recognizes it)
  (global-set-key (kbd "C-S-w") #'kill-current-buffer)

  ;; Tabs navigation like a browser
  (global-set-key (kbd "<C-prior>")  #'centaur-tabs-backward) ; Ctrl+PgUp
  (global-set-key (kbd "<C-next>")   #'centaur-tabs-forward)  ; Ctrl+PgDn
  (global-set-key (kbd "C-S-<prior>") #'centaur-tabs-move-current-tab-to-left)  ; Ctrl+Shift+PgUp
  (global-set-key (kbd "C-S-<next>")  #'centaur-tabs-move-current-tab-to-right) ; Ctrl+Shift+PgDn

  (defun metsatron/go-home ()
    (interactive)
    (if (get-buffer "*spacemacs*")
        (switch-to-buffer "*spacemacs*")
      (spacemacs-buffer/goto-buffer)))

  ;; Global fallback (fine), but…
  (global-set-key (kbd "C-t") #'metsatron/go-home)

  ;; …also an emulation-level override that beats minor modes
  (defvar metsatron/keys-emulation-mode t)
  (defvar metsatron/emulation-map (make-sparse-keymap))
  (define-key metsatron/emulation-map (kbd "C-t") #'metsatron/go-home)
  (add-to-list 'emulation-mode-map-alists
               `((metsatron/keys-emulation-mode . ,metsatron/emulation-map)))

  (with-eval-after-load 'centaur-tabs
    (require 'seq)

    (defun metsatron/ct-should-hide (buf)
      (let* ((name (buffer-name buf))
             (mode (buffer-local-value 'major-mode buf)))
        (or
         ;; names
         (string-prefix-p " *Treemacs" name)
         (string-prefix-p "*helm" name)     ;; *helm mini*, *helm M-x*, *Helm Find Files*
         (member name '("*Which Key*" "*spacemacs*" "*Messages*" "*scratch*"
                        "*Completions*" "*info*" "*Info*"))
         ;; modes
         (memq mode '(helm-major-mode spacemacs-buffer-mode which-key-mode
                                      treemacs-mode help-mode helpful-mode Info-mode)))))

    ;; Hard filter: remove after Centaur builds its list
    (advice-add 'centaur-tabs-buffer-list :filter-return
                (lambda (buffers)
                  (seq-remove #'metsatron/ct-should-hide buffers)))

    ;; Also turn tabs off inside these modes (belt & suspenders)
    (add-hook 'helm-major-mode-hook      #'centaur-tabs-local-mode)
    (add-hook 'spacemacs-buffer-mode-hook #'centaur-tabs-local-mode)
    (add-hook 'treemacs-mode-hook        #'centaur-tabs-local-mode)
    (add-hook 'Info-mode-hook            #'centaur-tabs-local-mode)

    ;; Return project name when available; otherwise fall back to our existing buckets
    (defun metsatron/ct-buffer-groups ()
      (list
       (cond
        ((or (string-prefix-p " *" (buffer-name))
             (member (buffer-name)
                     '("*spacemacs*" "*Messages*" "*Compile-Log*" "*Help*"
                       "*Warnings*" "*Backtrace*" "*Which Key*")))
         "Service")
        ((memq major-mode '(treemacs-mode vterm-mode term-mode
                                          magit-status-mode magit-process-mode package-menu-mode))
         "Tools")
        ((and (fboundp 'projectile-project-name) (projectile-project-p))
         (projectile-project-name))   ;; <-- per project
        ((buffer-file-name) "All")
        (t "Buffers"))))
    (setq centaur-tabs-buffer-groups-function #'metsatron/ct-buffer-groups)

    ;; Cycle groups (leave your C-S-PgUp/PgDn for moving tabs alone)
    (spacemacs/declare-prefix "ot" "tabs")
    (spacemacs/set-leader-keys
      "ot[" #'centaur-tabs-backward-group
      "ot]" #'centaur-tabs-forward-group)
    (global-set-key (kbd "M-<prior>") #'centaur-tabs-backward-group) ;; Alt+PgUp
    (global-set-key (kbd "M-<next>")  #'centaur-tabs-forward-group)  ;; Alt+PgDn

    ;; Force refresh
    (centaur-tabs-mode -1)
    (centaur-tabs-mode +1))

  ;; Ensure home buffer reflects recents on first startup
  (with-eval-after-load 'spacemacs-buffer
    (add-hook 'emacs-startup-hook
              (lambda ()
                (recentf-cleanup)
                (spacemacs-buffer/goto-buffer)))) )
