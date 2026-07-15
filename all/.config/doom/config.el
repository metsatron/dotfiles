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
;; Editor fonts — reproduce the Spacemacs visual grammar (was blk-fonts in
;; emacs.org). Observed live in the running Spacemacs: the `default' face
;; resolves to "SFMono Nerd Font Mono" and `variable-pitch' to "San Francisco
;; Display", both installed and resolving correctly (not fallbacks). Sizes are
;; POINT sizes (float), matching Spacemacs' declared :height 110 / 120. vterm
;; buffers override this with MesloLGS @ 11px — see the terminal section below.
(setq doom-font (font-spec :family "SFMono Nerd Font Mono" :size 11.0 :weight 'normal)
      doom-variable-pitch-font (font-spec :family "San Francisco Display" :size 12.0 :weight 'normal)
      doom-symbol-font (font-spec :family "Symbols Nerd Font Mono"))
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

;;; ===========================================================================
;;; vterm — terminal comfort (ported from Spacemacs blk-vterm-basics)
;;; ===========================================================================

;; The Claude TUI (since CLI v2.1.89) paints on the terminal's ALTERNATE SCREEN,
;; which writes nothing to the scrollback ring. CLAUDE_CODE_NO_FLICKER=1 is
;; Anthropic's own answer: alt-screen rendering with VIRTUALIZED scrollback,
;; reachable by forwarding scroll keys through to the app (see below). Set here
;; via setenv so it lands in process-environment and is inherited by the CLI
;; whichever client launches it.
;; https://github.com/anthropics/claude-code/issues/42670
(setenv "CLAUDE_CODE_NO_FLICKER" "1")

;; --- Terminal font picker ---------------------------------------------------
;; Preference order is declared in fonts.org; the first installed family wins,
;; so the order is load-bearing. IosevkaTerm is the tail guarantee, not the
;; choice. Height 105 renders an 11px glyph (measured), matching the rest of
;; Emacs and the standalone terminal.
(defvar metsatron/terminal-font-preference
  '("MesloLGS Nerd Font Mono"
    "FiraCode Nerd Font Mono"
    "Mononoki Nerd Font Mono"
    "IosevkaTerm Nerd Font Mono")
  "Monospace families for terminal buffers, most-preferred first.
Order is declared in `fonts.org'. `metsatron/terminal-font' picks the first
family that is actually installed.")

(defvar metsatron/terminal-font-height 105
  "Face height for terminal buffers (1/10 pt). At 105 MesloLGS renders an 11px
glyph, matching the rest of Emacs and the standalone terminal. Measure the
glyph, not the XLFD (Emacs reports pixel size 14 for the em box).")

(defun metsatron/terminal-font ()
  "First installed family from `metsatron/terminal-font-preference', or nil."
  (seq-find (lambda (family) (member family (font-family-list)))
            metsatron/terminal-font-preference))

;; --- Scroll a full-screen TUI (the Claude CLI) ------------------------------
;; Emacs binds the wheel to `mwheel-scroll' and S-PageUp to `scroll-down-command';
;; both scroll the one-screen-tall Emacs buffer and appear dead. In Claude
;; buffers ONLY, forward wheel + S-PageUp/Down to the application. A plain shell
;; vterm keeps Emacs-side scrolling — it has a real scrollback ring.
(defun metsatron/claude-tui-buffer-p ()
  "Non-nil if the current buffer hosts a Claude CLI TUI on the alternate screen."
  (and (derived-mode-p 'vterm-mode)
       (string-match-p "claude" (buffer-name))))

(defun metsatron/claude-scroll-back (&optional _event)
  "Scroll the Claude TUI back a page (send PageUp to the application)."
  (interactive)
  (vterm-send-prior))

(defun metsatron/claude-scroll-forward (&optional _event)
  "Scroll the Claude TUI forward a page (send PageDown to the application)."
  (interactive)
  (vterm-send-next))

(defun metsatron/claude-scroll-keys ()
  "Route scroll gestures to the CLI in Claude buffers instead of to Emacs."
  (when (metsatron/claude-tui-buffer-p)
    (let ((map (make-sparse-keymap)))
      (set-keymap-parent map (current-local-map))
      ;; wheel: X11 sends mouse-4/5, GUI Emacs also sends wheel-up/down
      (define-key map [wheel-up]        #'metsatron/claude-scroll-back)
      (define-key map [wheel-down]      #'metsatron/claude-scroll-forward)
      (define-key map [mouse-4]         #'metsatron/claude-scroll-back)
      (define-key map [mouse-5]         #'metsatron/claude-scroll-forward)
      (define-key map (kbd "S-<prior>") #'metsatron/claude-scroll-back)
      (define-key map (kbd "S-<next>")  #'metsatron/claude-scroll-forward)
      (use-local-map map))))

;; --- vterm-copy-mode auto-freeze --------------------------------------------
;; Freeze output when you scroll off the bottom (so live output doesn't yank you
;; down while reading); unfreeze automatically when you type. Never blocks input.
;; NOTE: this is the AUTHORITATIVE version. emacs.org's blk-vterm-basics carried
;; two earlier, dead redefinitions of these same defuns (superseded in place) —
;; that accidental sediment is deliberately NOT reproduced here.
(defvar la/vterm--write-commands
  '(self-insert-command newline newline-and-indent open-line
    vterm-yank vterm-send-string vterm-send-return
    evil-insert evil-append evil-append-line
    evil-open-below evil-open-above
    evil-change evil-change-line evil-substitute evil-replace
    evil-delete-char evil-delete-backward-char
    evil-paste-after evil-paste-before)
  "Commands that must not run while vterm-copy-mode is active.")

(defun la/vterm--writing-command-p ()
  (or (and (boundp 'evil-state)
           (or (evil-insert-state-p) (evil-replace-state-p)))
      (memq this-command la/vterm--write-commands)))

(defun la/vterm-prevent-read-only-errors ()
  "Before a write-like command, drop out of vterm-copy-mode."
  (when (and (derived-mode-p 'vterm-mode)
             vterm-copy-mode
             (la/vterm--writing-command-p))
    (vterm-copy-mode -1)
    (goto-char (point-max))))

(defun la/vterm--at-bottom-visible-p ()
  "Non-nil when point-max is fully visible in the selected window."
  (let ((pm (point-max)))
    (and (pos-visible-in-window-p pm)
         (save-excursion
           (goto-char pm)
           (eq (window-end (selected-window) t) pm)))))

(defun la/vterm-freeze-when-scrolled ()
  "Enable vterm-copy-mode when not following the bottom."
  (when (derived-mode-p 'vterm-mode)
    (if (la/vterm--at-bottom-visible-p)
        (when vterm-copy-mode (vterm-copy-mode -1))
      (unless (or vterm-copy-mode (la/vterm--writing-command-p))
        (vterm-copy-mode 1)))))

(defun la/vterm-follow-bottom ()
  "Jump to end and resume following output."
  (interactive)
  (goto-char (point-max))
  (when vterm-copy-mode (vterm-copy-mode -1)))

(after! vterm
  ;; SINGLE OWNER of vterm-max-scrollback (primary screen only; a full-screen
  ;; TUI on the alternate screen writes no ring, so raising this won't give the
  ;; Claude buffer scrollback).
  (setq vterm-max-scrollback 100000)

  (defun metsatron/vterm-fonts ()
    (variable-pitch-mode 0)
    ;; turn off prettify-symbols (can distort TUIs)
    (setq-local prettify-symbols-alist nil)
    (when (boundp 'prettify-symbols-mode) (prettify-symbols-mode -1))
    (when-let ((family (metsatron/terminal-font)))
      (let ((spec `(:family ,family :height ,metsatron/terminal-font-height)))
        (face-remap-add-relative 'default     spec)
        (face-remap-add-relative 'fixed-pitch spec)))
    (setq-local line-spacing 0))

  (defun la/vterm-install-freeze-hooks ()
    (add-hook 'pre-command-hook  #'la/vterm-prevent-read-only-errors nil t)
    (add-hook 'post-command-hook #'la/vterm-freeze-when-scrolled     nil t))

  (add-hook 'vterm-mode-hook #'metsatron/vterm-fonts)
  (add-hook 'vterm-mode-hook #'metsatron/claude-scroll-keys)
  (add-hook 'vterm-mode-hook #'la/vterm-install-freeze-hooks))

;;; ===========================================================================
;;; Claude Code inside Doom — claude-code-ide (from emacs.org blk-claude-agents)
;;; ===========================================================================

;; The harness-preserving client: runs the real `claude' CLI in a vterm buffer,
;; so every hook/skill/plugin in the DotCortex harness fires exactly as in a bare
;; terminal, AND bridges Emacs to Claude over MCP (xref, imenu, project info,
;; flycheck exposed as tools). The default for real DotCortex work.
;;
;; Only this one client of emacs.org's three is ported; agent-shell and the thin
;; claude-code wrapper are deferred. CLAUDE_CODE_NO_FLICKER=1 is already exported
;; in the vterm section above, so the CLI inherits it whichever way it launches.
(after! claude-code-ide
  ;; Expose Emacs to Claude over MCP.
  (when (fboundp 'claude-code-ide-emacs-tools-setup)
    (claude-code-ide-emacs-tools-setup)))

;; Mnemonic leader keys, matching the Spacemacs bindings: c = menu, o = toggle.
;; (claude-code-ide-menu / -toggle are autoloaded, so binding pre-load is fine.)
(map! :leader
      :desc "Claude Code IDE menu"   "o c" #'claude-code-ide-menu
      :desc "Claude Code IDE toggle" "o o" #'claude-code-ide-toggle)
