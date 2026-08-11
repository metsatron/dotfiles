;;; init.el -*- lexical-binding: t; -*-
;; Classic sanctuary Emacs.  Selected Org/Evil behavior is adapted from the
;; canonical DotCortex Doom and Spacemacs profiles; this file intentionally
;; has no Doom, Spacemacs, Treemacs, or tab-bar dependency.

(require 'cl-lib)
(require 'seq)

;;; --------------------------------------------------------------------------
;;; Runtime state, files, and a small comfortable UI

(defgroup metsatron-classic-emacs nil
  "Vanilla Emacs settings shared by the classic DotCortex sanctuaries."
  :group 'convenience)

(defcustom metsatron/classic-emacs-cache-directory
  (expand-file-name "~/.cache/emacs-classic/")
  "Directory for mutable vanilla Emacs caches and session files."
  :type 'directory
  :group 'metsatron-classic-emacs)

(defcustom metsatron/classic-emacs-runtime-directory
  (expand-file-name "~/.config/emacs-classic/")
  "Directory for mutable classic-profile customization and theme state."
  :type 'directory
  :group 'metsatron-classic-emacs)

(make-directory metsatron/classic-emacs-cache-directory t)
(make-directory metsatron/classic-emacs-runtime-directory t)

(setq vc-follow-symlinks t
      inhibit-startup-screen t
      initial-scratch-message nil
      ring-bell-function #'ignore
      ;; Keep the native GNUstep/NS file panel available.  A nil
      ;; `use-dialog-box' makes the Open command fall back to Emacs' own
      ;; minibuffer reader, which is the opposite of the classic sanctuary
      ;; file-manager contract.
      use-dialog-box t
      use-file-dialog t
      sentence-end-double-space nil
      backup-directory-alist
      `(("." . ,(expand-file-name "backups/" metsatron/classic-emacs-cache-directory)))
      auto-save-file-name-transforms
      `((".*" ,(expand-file-name "auto-saves/" metsatron/classic-emacs-cache-directory) t))
      custom-file
      (expand-file-name "custom.el" metsatron/classic-emacs-runtime-directory)
      savehist-file
      (expand-file-name "savehist" metsatron/classic-emacs-cache-directory)
      recentf-save-file
      (expand-file-name "recentf" metsatron/classic-emacs-cache-directory)
      save-place-file
      (expand-file-name "saveplace" metsatron/classic-emacs-cache-directory)
      project-list-file
      (expand-file-name "projects" metsatron/classic-emacs-cache-directory)
      url-history-file
      (expand-file-name "url-history" metsatron/classic-emacs-cache-directory)
      use-short-answers t
      scroll-conservatively 101
      scroll-margin 3
      frame-inhibit-implied-resize t)

(when (file-readable-p custom-file)
  (load custom-file nil t))
(savehist-mode 1)
(recentf-mode 1)
(save-place-mode 1)
(global-auto-revert-mode 1)
(winner-mode 1)
(delete-selection-mode 1)

(defcustom metsatron/classic-emacs-fixed-font
  "SFMono Nerd Font Mono"
  "Preferred fixed-pitch family for source, tables, and code blocks."
  :type 'string
  :group 'metsatron-classic-emacs)

(defcustom metsatron/classic-emacs-variable-font
  "San Francisco Display"
  "Preferred variable-pitch family for prose and Org headings."
  :type 'string
  :group 'metsatron-classic-emacs)

(defcustom metsatron/classic-emacs-font-height 110
  "Default face height in units of one tenth of a point."
  :type 'integer
  :group 'metsatron-classic-emacs)

(defun metsatron/classic-emacs--set-face-family (face family height)
  "Set FACE to FAMILY and HEIGHT when FAMILY is installed.
FACE is a face symbol, FAMILY is a font family name, and HEIGHT is an Emacs
face height.  Missing optional sanctuary fonts are silently left to the theme."
  (when (and (facep face)
             (stringp family)
             (member family (font-family-list)))
    (set-face-attribute face nil :family family :height height)))

(metsatron/classic-emacs--set-face-family
 'default metsatron/classic-emacs-fixed-font metsatron/classic-emacs-font-height)
(metsatron/classic-emacs--set-face-family
 'fixed-pitch metsatron/classic-emacs-fixed-font metsatron/classic-emacs-font-height)
(metsatron/classic-emacs--set-face-family
 'variable-pitch metsatron/classic-emacs-variable-font 120)

;;; --------------------------------------------------------------------------
;;; Per-sanctuary themes

(defcustom metsatron/classic-emacs-theme-by-display
  '((":90" . modus-operandi)
    (":91" . tango)
    (":92" . tsdh-light)
    (":93" . leuven)
    (":94" . modus-vivendi)
    (":95" . tsdh-light)
    (":96" . modus-operandi))
  "Default built-in themes keyed by sanctuary Xephyr display.
The theme file written by a sanctuary scheme switch overrides this table."
  :type '(alist :key-type (string :tag "Display")
                :value-type (symbol :tag "Theme"))
  :group 'metsatron-classic-emacs)

(defvar metsatron/classic-emacs-active-theme nil
  "Theme currently loaded by the classic sanctuary profile.")

(defun metsatron/classic-emacs--display-key ()
  "Return the current X display in the normalized form used by theme maps."
  (replace-regexp-in-string
   "\\.0\\'" "" (or (getenv "DISPLAY") "")))

(defcustom metsatron/classic-emacs-native-toolbar-by-display
  '((":91" . t))
  "Whether to show Emacs' native toolbar on each classic sanctuary display.
GNUstep's NSToolbar buttons are drawn by GNUstep GUI's active theme rather
than by Emacs' `tool-bar' face.  The NeXT/Tango GNUstep room keeps the native
toolbar available so its Open command remains reachable; other classic
sanctuaries retain the usual Emacs toolbar unless they are listed here.  The
toolbar remains available through `M-x metsatron/classic-emacs-toggle-native-toolbar'."
  :type '(alist :key-type (string :tag "Display")
                :value-type (boolean :tag "Show native toolbar"))
  :group 'metsatron-classic-emacs)

(defun metsatron/classic-emacs--native-toolbar-enabled-p ()
  "Return the native toolbar policy for the current sanctuary display."
  (let ((override (assoc (metsatron/classic-emacs--display-key)
                         metsatron/classic-emacs-native-toolbar-by-display)))
    (if override (cdr override) t)))

(defun metsatron/classic-emacs--style-toolbar-face ()
"Keep Emacs' toolbar face on a classic neutral surface.
This protects the Emacs-owned toolbar face for sanctuaries where the native
toolbar is enabled; GNUstep's theme-owned NSToolbar buttons may still use
their own theme surfaces."
  (when (facep 'tool-bar)
    (set-face-attribute 'tool-bar nil
                        :background "grey75"
                        :foreground "black"
                        :box '(:line-width 1 :style released-button))))

(defun metsatron/classic-emacs-open-file ()
  "Open a file with the native sanctuary panel when this Emacs provides one.
GNUstep Emacs exposes `ns-open-file-using-panel', but its stock toolbar
binding `menu-find-file-existing' still falls back to the minibuffer in this
build.  Keep the ordinary Emacs command as the portable fallback."
  (interactive)
  (if (and (eq window-system 'ns)
           (fboundp 'ns-open-file-using-panel))
      (call-interactively #'ns-open-file-using-panel)
    (call-interactively #'menu-find-file-existing)))

(defun metsatron/classic-emacs--apply-native-toolbar ()
  "Apply the per-display native toolbar policy and its neutral face."
  (metsatron/classic-emacs--style-toolbar-face)
  (when (fboundp 'tool-bar-mode)
    (tool-bar-mode (if (metsatron/classic-emacs--native-toolbar-enabled-p)
                       1
                     -1)))
  (when (boundp 'tool-bar-map)
    (define-key tool-bar-map [open-file] #'metsatron/classic-emacs-open-file)))

(defun metsatron/classic-emacs-toggle-native-toolbar ()
  "Toggle the native toolbar in the current classic Emacs instance."
  (interactive)
  (when (fboundp 'tool-bar-mode)
    (tool-bar-mode (if (bound-and-true-p tool-bar-mode) -1 1))
    (metsatron/classic-emacs--style-toolbar-face)
    (message "Classic Emacs native toolbar: %s"
             (if (bound-and-true-p tool-bar-mode) "shown" "hidden"))))

(defun metsatron/classic-emacs--theme-file ()
  "Return the mutable theme override file for this sanctuary."
  (expand-file-name "classic-theme.el" metsatron/classic-emacs-runtime-directory))

(defun metsatron/classic-emacs--default-theme ()
  "Return the built-in default theme for the current sanctuary display."
  (or (cdr (assoc (metsatron/classic-emacs--display-key)
                  metsatron/classic-emacs-theme-by-display))
      'tango))

(defun metsatron/classic-emacs--read-theme-file ()
  "Load the mutable theme override and return its requested theme symbol."
  (let ((metsatron/classic-emacs-theme nil)
        (file (metsatron/classic-emacs--theme-file)))
    (when (file-readable-p file)
      (load file nil t))
    (and (boundp 'metsatron/classic-emacs-theme)
         (symbolp metsatron/classic-emacs-theme)
         metsatron/classic-emacs-theme)))

(defun metsatron/classic-emacs--load-theme (theme)
  "Load THEME without prompting and refresh existing Org buffers.
THEME must be a symbol available in `custom-available-themes'."
  (if (not (memq theme (custom-available-themes)))
      (message "Classic Emacs theme unavailable: %s" theme)
    (mapc #'disable-theme custom-enabled-themes)
    (condition-case err
        (progn
          (load-theme theme t)
          (setq metsatron/classic-emacs-active-theme theme)
          (dolist (buffer (buffer-list))
            (with-current-buffer buffer
              (when (derived-mode-p 'org-mode)
                (metsatron/classic-org-apply-faces))))
          (message "Classic sanctuary Emacs theme: %s" theme))
      (error
       (message "Classic Emacs could not load theme %s: %s" theme
                (error-message-string err))))))

(defun metsatron/classic-emacs-refresh-theme ()
  "Reload the sanctuary's mutable theme override without restarting Emacs.
This is called by Redstone's Desktop Scheme applier through `emacsclient'."
  (interactive)
  (metsatron/classic-emacs--load-theme
   (or (metsatron/classic-emacs--read-theme-file)
       (metsatron/classic-emacs--default-theme))))

(add-to-list 'custom-theme-load-path metsatron/classic-emacs-runtime-directory)
(metsatron/classic-emacs-refresh-theme)
(metsatron/classic-emacs--apply-native-toolbar)

;;; --------------------------------------------------------------------------
;;; Evil and Colemak-NEIO

(setq evil-want-keybinding nil
      evil-want-C-u-scroll t
      evil-want-Y-yank-to-eol t
      evil-undo-system 'undo-redo)

(when (require 'evil nil t)
  ;; The intercept layer is the same proven shape used by the Doom and
  ;; Spacemacs profiles, but it does not depend on evil-collection.  That keeps
  ;; the vanilla room small while preserving operator-pending motions (dn/de/di).
  (defvar metsatron/classic-neio-intercept-map (make-sparse-keymap)
    "Highest-priority Colemak-NEIO map for the classic sanctuary profile.")

  (define-minor-mode metsatron/classic-neio-mode
    "Enforce Colemak-NEIO at Evil intercept priority."
    :global t
    :keymap metsatron/classic-neio-intercept-map)

  (defun metsatron/classic-search-next ()
    "Move to the next active Evil search result."
    (interactive)
    (if (bound-and-true-p evil-ex-search-pattern)
        (evil-ex-search-next)
      (evil-search-next)))

  (defun metsatron/classic-search-previous ()
    "Move to the previous active Evil search result."
    (interactive)
    (if (bound-and-true-p evil-ex-search-pattern)
        (evil-ex-search-previous)
      (evil-search-previous)))

  (metsatron/classic-neio-mode 1)
  (dolist (state '(normal motion visual operator))
    (evil-make-intercept-map
     (evil-get-auxiliary-keymap
      metsatron/classic-neio-intercept-map state t t)
     state))

  (evil-define-key 'normal metsatron/classic-neio-intercept-map
    (kbd "n") #'evil-backward-char
    (kbd "e") #'evil-next-line
    (kbd "i") #'evil-previous-line
    (kbd "o") #'evil-forward-char
    (kbd "h") #'metsatron/classic-search-next
    (kbd "H") #'metsatron/classic-search-previous
    (kbd "k") #'evil-insert
    (kbd "K") #'evil-insert-line
    (kbd "l") #'evil-open-below
    (kbd "L") #'evil-open-above)

  (evil-define-key '(motion visual) metsatron/classic-neio-intercept-map
    (kbd "n") #'evil-backward-char
    (kbd "e") #'evil-next-line
    (kbd "i") #'evil-previous-line
    (kbd "o") #'evil-forward-char
    (kbd "h") #'metsatron/classic-search-next
    (kbd "H") #'metsatron/classic-search-previous)

  (evil-define-key 'operator metsatron/classic-neio-intercept-map
    (kbd "n") #'evil-backward-char
    (kbd "e") #'evil-next-line
    (kbd "i") #'evil-previous-line
    (kbd "o") #'evil-forward-char)

  ;; C-w keeps Evil's window prefix, with its directions translated to NEIO.
  (define-key evil-window-map (kbd "n") #'evil-window-left)
  (define-key evil-window-map (kbd "e") #'evil-window-down)
  (define-key evil-window-map (kbd "i") #'evil-window-up)
  (define-key evil-window-map (kbd "o") #'evil-window-right)

  ;; Keep a visual selection after shifting it, matching the existing Doom and
  ;; Spacemacs profiles.  Plain i remains upward only in Visual state.
  (define-key evil-visual-state-map (kbd "i") #'evil-previous-line)
  (define-key evil-visual-state-map (kbd "I") nil)
  (setq evil-shift-round nil)
  (define-key evil-visual-state-map (kbd "<") #'evil-shift-left)
  (define-key evil-visual-state-map (kbd ">") #'evil-shift-right)
  (advice-add 'evil-shift-right :after
              (lambda (&rest _) (when (eq evil-state 'visual)
                                  (evil-visual-restore))))
  (advice-add 'evil-shift-left :after
              (lambda (&rest _) (when (eq evil-state 'visual)
                                  (evil-visual-restore))))
  (evil-mode 1))

;;; --------------------------------------------------------------------------
;;; Org-mode: tables, images, source blocks, and readable prose

(defcustom metsatron/classic-org-heading-heights '(155 140 125 112)
  "Face heights for the first four Org heading levels."
  :type '(repeat integer)
  :group 'metsatron-classic-emacs)

(defvar metsatron/classic-org-stars-hidden t
  "Whether leading Org heading stars are visually hidden.")

(defvar metsatron/classic-org--hide-stars-rule
  '(("^\\(\\*+\\) " (1 'org-hide)))
  "Font-lock rule used to hide Org heading stars without changing the text.")

(defun metsatron/classic-org-apply-faces ()
  "Apply theme-inherited faces to the current Org buffer.
The function changes weight, pitch, and scale only; theme colours remain owned
by the active sanctuary theme."
  (when (derived-mode-p 'org-mode)
    (set-face-attribute 'org-document-title nil
                        :inherit 'variable-pitch :weight 'bold)
    (set-face-attribute 'org-document-info nil
                        :inherit 'variable-pitch :weight 'bold)
    (cl-loop for level from 1 to 4
             for face = (intern (format "org-level-%d" level))
             for height in metsatron/classic-org-heading-heights
             do (set-face-attribute face nil
                                    :inherit 'variable-pitch
                                    :weight 'bold
                                    :height height))
    (dolist (level '(5 6 7 8))
      (set-face-attribute (intern (format "org-level-%d" level)) nil
                          :inherit 'variable-pitch
                          :weight 'bold
                          :height 110))
    (dolist (face '(org-code org-verbatim org-table org-block
                    org-block-begin-line org-block-end-line org-meta-line
                    org-special-keyword org-checkbox))
      (set-face-attribute face nil :inherit 'fixed-pitch))))

(defun metsatron/classic-org--apply-stars-visibility ()
  "Apply the Doom/Spacemacs-style hidden heading-star presentation."
  (setq-local org-hide-leading-stars nil)
  (font-lock-remove-keywords nil metsatron/classic-org--hide-stars-rule)
  (when metsatron/classic-org-stars-hidden
    (font-lock-add-keywords nil metsatron/classic-org--hide-stars-rule 'append))
  (set-face-attribute 'org-hide nil :foreground nil :inherit 'shadow)
  (font-lock-flush)
  (font-lock-ensure))

(defun metsatron/classic-org-toggle-pretty ()
  "Toggle Org emphasis markers and leading stars in the current buffer."
  (interactive)
  (setq-local org-hide-emphasis-markers (not org-hide-emphasis-markers))
  (setq metsatron/classic-org-stars-hidden
        (not metsatron/classic-org-stars-hidden))
  (metsatron/classic-org--apply-stars-visibility)
  (font-lock-flush)
  (font-lock-ensure))

(defun metsatron/classic-org-looks ()
  "Enable the polished Org presentation for the current buffer."
  (variable-pitch-mode 1)
  (org-indent-mode 1)
  (visual-line-mode 1)
  (setq-local truncate-lines nil
              electric-indent-inhibit t)
  (display-line-numbers-mode 1)
  (face-remap-add-relative 'line-number
                           '(:family "SFMono Nerd Font Mono" :height 0.82))
  (face-remap-add-relative 'line-number-current-line
                           '(:family "SFMono Nerd Font Mono" :height 0.82))
  (metsatron/classic-org-apply-faces)
  (metsatron/classic-org--apply-stars-visibility)
  (when (fboundp 'valign-mode)
    (valign-mode 1))
  (when (fboundp 'org-modern-mode)
    (org-modern-mode 1))
  (when (fboundp 'org-appear-mode)
    (org-appear-mode 1)))

(with-eval-after-load 'org
  (setq org-directory "~/org/"
        org-startup-with-inline-images t
        org-startup-indented t
        org-startup-folded 'showeverything
        org-hide-emphasis-markers t
        org-hide-leading-stars nil
        org-pretty-entities t
        org-ellipsis "…"
        org-startup-truncated nil
        org-return-follows-link t
        org-src-tab-acts-natively t
        org-src-preserve-indentation t
        org-edit-src-content-indentation 0
        org-src-fontify-natively t
        org-src-window-setup 'current-window
        org-image-actual-width nil
        org-export-with-sub-superscripts '{}
        org-export-with-broken-links t
        org-table-auto-align t
        org-use-speed-commands t
        org-confirm-babel-evaluate t)
  ;; Native GNUstep Emacs was built without a Tree-sitter parser module.
  ;; Keep Emacs Lisp and shell Babel available everywhere, and only register
  ;; Python when this particular Emacs can actually provide Tree-sitter.
  (let ((languages '((emacs-lisp . t) (shell . t))))
    (when (and (fboundp 'treesit-available-p)
               (treesit-available-p))
      (push '(python . t) languages))
    (org-babel-do-load-languages 'org-babel-load-languages languages))
  (define-key org-mode-map (kbd "C-c e") #'metsatron/classic-org-toggle-pretty)
  (define-key org-mode-map (kbd "C-c i") #'org-toggle-inline-images)
  (add-hook 'org-mode-hook #'metsatron/classic-org-looks)
  (add-hook 'org-src-mode-hook
            (lambda () (setq-local electric-indent-inhibit t))))

;; `org-modern' is used for tables only.  The explicit nil values prevent it
;; from painting headings, stars, lists, checkboxes, blocks, and timestamps.
(with-eval-after-load 'org-modern
  (setq org-modern-table t
        org-modern-star nil
        org-modern-hide-stars nil
        org-modern-list nil
        org-modern-checkbox nil
        org-modern-todo nil
        org-modern-tag nil
        org-modern-priority nil
        org-modern-timestamp nil
        org-modern-block-name nil
        org-modern-keyword nil))

(with-eval-after-load 'valign
  (setq valign-fancy-bar t))

(with-eval-after-load 'org-appear
  (setq org-appear-autolinks t
        org-appear-autoentities t
        org-appear-autosubmarkers t))

(with-eval-after-load 'org-download
  (setq org-download-method 'directory
        org-download-image-dir "./images"
        org-download-heading-lvl nil
        org-download-timestamp "%Y%m%d-%H%M%S_"))

(require 'org-modern nil t)
(require 'valign nil t)
(require 'org-appear nil t)
(require 'org-download nil t)
(require 'org)

;;; --------------------------------------------------------------------------
;;; Small universal conveniences; no tabs or project drawer

(global-set-key (kbd "C-=") #'text-scale-increase)
(global-set-key (kbd "C--") #'text-scale-decrease)
(global-set-key (kbd "C-0") #'text-scale-adjust)
(global-set-key (kbd "C-x C-b") #'ibuffer)

(add-hook 'after-make-frame-functions
          (lambda (_frame)
            (metsatron/classic-emacs--set-face-family
             'default metsatron/classic-emacs-fixed-font metsatron/classic-emacs-font-height)
            (metsatron/classic-emacs--set-face-family
             'variable-pitch metsatron/classic-emacs-variable-font 120)))

;;; --------------------------------------------------------------------------
;;; Named server for live sanctuary theme switching

(require 'server)
(defcustom metsatron/classic-emacs-server-directory
  (expand-file-name "server/" metsatron/classic-emacs-cache-directory)
  "Shared guest-home socket directory for live classic Emacs clients.
The path is deliberately inside the mounted sanctuary home rather than
`/run/user`, so emacsclient and external IDE integrations can reach the native
GNUstep Emacs server from the host when the room is running."
  :type 'directory
  :group 'metsatron-classic-emacs)

(make-directory metsatron/classic-emacs-server-directory t)
(set-file-modes metsatron/classic-emacs-server-directory #o700)
(setq server-socket-dir metsatron/classic-emacs-server-directory)
(setq server-name
      (format "classic-%s"
              (replace-regexp-in-string
               "[^[:alnum:]]+" "" (metsatron/classic-emacs--display-key))))
(unless (server-running-p server-name)
  (condition-case err
      (server-start)
    (error (message "Classic Emacs server unavailable: %s"
                    (error-message-string err)))))

;; Keep this after the first theme load so Org's theme-sensitive faces settle
;; before an already-open buffer is displayed.
(add-hook 'after-load-theme-hook
          (lambda (&rest _)
            (metsatron/classic-emacs--style-toolbar-face)
            (metsatron/classic-org-apply-faces)))

;;; init.el ends here
