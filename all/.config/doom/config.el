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

;; NOTE: the old interactive `la/workbench' (delete-other-windows on the LIVE
;; frame) is REMOVED. That is precisely the destructive pattern the hardened
;; layout system at the end of this file exists to replace — an interactive
;; command that rearranges the frame you are standing in, one M-M-completion
;; away from demolishing your live workspace. See "@Claude / @Workbench layouts"
;; below; `SPC o w' now SWITCHES TO the @Workbench workspace instead.

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

;;; ===========================================================================
;;; @Claude / @Workbench layouts (from emacs.org blk-claude-workspace)
;;; ===========================================================================
;;
;; Ported to Doom's :ui workspaces (persp-mode) from Spacemacs' custom layouts.
;; The kernel and builders are pure window elisp and cross over unchanged; only
;; the REGISTRATION differs (spacemacs|define-custom-layout -> +workspace-switch).
;;
;; The whole design rests on one distinction: these are LAYOUTS, not window
;; commands. Each door switches to (creating) a dedicated workspace FIRST, then
;; builds inside it — so invoking one leaves your current workspace intact.
;; "New" means ADDITIONAL, not IN PLACE OF.

(defvar metsatron/claude-workspace-width 80
  "Columns for the Claude window in the @Claude layout.
80 because this window is a TERMINAL, not a pane of prose — it hosts vterm and
the Claude CLI's TUI, both written against the traditional 80-column terminal.
Wider just stretches the same wrapped output and starves the editor pane.")

(defvar metsatron/claude-workspace-treemacs-width 20
  "Columns for the Treemacs side window in both layouts.")

(defvar metsatron/claude-workspace-term-height 10
  "USABLE lines for the vterm strip beneath the Claude panel in @Claude.
This is the loom console — a first-class part of the workspace, not a garnish.
Body lines, not total: `split-window' sizes the TOTAL window, so the mode line
eats into it; the split is normalised against `window-body-*' afterward.")

(defvar metsatron/workbench-term-height 8
  "Lines for the vterm strip in the @Workbench layout.")

;;; --- Layout kernel -------------------------------------------------------

(defun metsatron/layout--reset ()
  "Collapse the current workspace to ONE ordinary window. Deliberately paranoid.

`delete-other-windows' is a FALSE RESET: side windows (Treemacs) are exempt, and
claude-code-ide stamps its window with `no-delete-other-windows' which vetoes it.
Two things make this reliable: (1) `window-side' also lives on INTERNAL parent
windows that `window-list' never returns, so the tree is walked in FULL (clearing
only leaves leaves the tree corrupt: \"Window X has not same side left as its
parent\"); (2) `ignore-window-parameters' is bound so the veto cannot fire.

Deletes WINDOWS, never buffers or processes — no Claude session dies here."
  (letrec ((clear (lambda (w)
                    (set-window-parameter w 'window-side nil)
                    (set-window-parameter w 'window-slot nil)
                    (set-window-parameter w 'no-delete-other-windows nil)
                    (let ((c (window-child w)))
                      (while c
                        (funcall clear c)
                        (setq c (window-next-sibling c)))))))
    (funcall clear (frame-root-window)))
  (let ((ignore-window-parameters t))
    (delete-other-windows))
  ;; Transient popups can otherwise reclaim a side slot the moment we rebuild.
  (dolist (name '("*helm mini*" "*helm buffers*" "*which-key*" "*doom*"))
    (when (get-buffer name)
      (let ((kill-buffer-query-functions nil))
        (ignore-errors (kill-buffer name))))))

(defun metsatron/layout--editor-buffer ()
  "A real file buffer for the editor pane.
Must visit a file: a scratch buffer merely named \"claude\" is not an editor
pane. Falls back to *scratch* only when nothing else exists."
  (or (seq-find (lambda (b)
                  (and (buffer-file-name b)
                       (not (string-prefix-p " " (buffer-name b)))))
                (buffer-list))
      (get-buffer-create "*scratch*")))

(defun metsatron/layout--treemacs ()
  "Open Treemacs, then return to the sole ordinary window."
  (when (fboundp 'treemacs) (treemacs))
  (when (fboundp 'treemacs-set-width)
    (treemacs-set-width metsatron/claude-workspace-treemacs-width))
  (when-let ((editor (seq-find (lambda (w) (not (window-parameter w 'window-side)))
                               (window-list))))
    (select-window editor)))

(defun metsatron/layout--vterm-in (window)
  "Put a shell in WINDOW — reusing the existing *vterm* rather than spawning."
  (select-window window)
  (if-let ((existing (get-buffer "*vterm*")))
      (set-window-buffer window existing)
    (if (fboundp 'vterm) (vterm) (ansi-term (or (getenv "SHELL") "/bin/bash")))))

(defun metsatron/claude--live-buffer ()
  "A Claude TUI buffer with a LIVE process, from ANY client, or nil.
ADOPTING a running session is the only safe move: the old builder started a fresh
CLI with `-r' that raced a live session and killed it, taking the user's window.
Never spawn a Claude when one is running; never do window surgery around a live
Claude buffer beyond moving it."
  (let ((ide (and (fboundp 'claude-code-ide--get-buffer-name)
                  (get-buffer (claude-code-ide--get-buffer-name)))))
    (or (and ide (get-buffer-process ide) ide)
        (seq-find (lambda (b)
                    (and (buffer-live-p b)
                         (string-match-p "claude" (buffer-name b))
                         (with-current-buffer b (derived-mode-p 'vterm-mode))
                         (get-buffer-process b)))
                  (buffer-list)))))

;;; --- Builders (NON-interactive on purpose — see the doors below) ----------

(defun metsatron/claude-workspace-build ()
  "Treemacs | editor | [ Claude / vterm ]. NOT interactive by design."
  (metsatron/layout--reset)
  (switch-to-buffer (metsatron/layout--editor-buffer))
  (metsatron/layout--treemacs)
  (let* ((editor (selected-window))
         (right  (split-window-right
                  (max 40 (- (window-total-width editor)
                             metsatron/claude-workspace-width))))
         (claude (metsatron/claude--live-buffer)))
    (if claude
        ;; ADOPT the running session — `set-window-buffer' only moves the buffer,
        ;; never touches the process, so the session cannot die here.
        (set-window-buffer right claude)
      ;; Nothing running: start one. The width defcustom is set GLOBALLY (not
      ;; let-bound) because claude-code-ide displays the buffer ASYNCHRONOUSLY,
      ;; after any `let' here has exited (a let-bound 80 came out as 98).
      (delete-window right)
      (setq claude-code-ide-use-side-window t
            claude-code-ide-window-side 'right
            claude-code-ide-window-width metsatron/claude-workspace-width)
      (claude-code-ide)
      (setq right (and (fboundp 'claude-code-ide--get-buffer-name)
                       (get-buffer-window (claude-code-ide--get-buffer-name)))))
    ;; vterm strip UNDER the Claude panel — the loom console. A NEGATIVE size
    ;; means "give the NEW window this many lines"; sizing the split directly is
    ;; deterministic. A post-hoc window-resize against window-body-height was
    ;; tried and is WRONG — the window has not settled, so the layout DRIFTS a
    ;; line per rebuild (vterm 11->12, Claude 37->38). Do not reintroduce it.
    (when (window-live-p right)
      (let ((term (split-window right
                                (- (1+ metsatron/claude-workspace-term-height))
                                'below)))
        (metsatron/layout--vterm-in term)))
    ;; Width IS safe to normalise: measured against the settled editor split.
    (when (window-live-p right)
      (let ((dw (- metsatron/claude-workspace-width (window-body-width right))))
        (unless (zerop dw) (ignore-errors (window-resize right dw t)))))
    (when (window-live-p editor) (select-window editor)))
  ;; Resync the PTY: vterm learns its size from the window, and after the splits
  ;; the CLI still renders for the OLD width (garbled interleaved output).
  ;; `claude-code-ide--sync-terminal-dimensions' takes (BUFFER WINDOW). It was
  ;; once called with NO args inside `ignore-errors' — raising
  ;; wrong-number-of-arguments into the void, a silent no-op every time. Guard the
  ;; CONDITION, not the CALL: never wrap a call in ignore-errors to make it "safe".
  (when-let* (((fboundp 'claude-code-ide--sync-terminal-dimensions))
              (buf (metsatron/claude--live-buffer))
              (win (get-buffer-window buf)))
    (claude-code-ide--sync-terminal-dimensions buf win)))

(defun metsatron/workbench-build ()
  "Treemacs | [ document / vterm ] | document — two docs side by side.
NOT interactive by design."
  (metsatron/layout--reset)
  (switch-to-buffer (metsatron/layout--editor-buffer))
  (metsatron/layout--treemacs)
  (let* ((left  (selected-window))
         (right (split-window-right)))
    (select-window left)
    (let ((term (split-window left
                              (- (window-total-height left)
                                 metsatron/workbench-term-height)
                              'below)))
      (metsatron/layout--vterm-in term))
    (when (window-live-p right) (select-window right))))

;;; --- The doors: interactive, workspace-first, hence SAFE ------------------
;;
;; `(interactive)' is a CAPABILITY GRANT, not a convenience: it publishes a
;; command to M-x and every completion frontend, where a destructive one gets
;; selected by accident eventually (which is how the old workbench got demolished,
;; 2026-07-13). The BUILDERS above are therefore NOT interactive. These doors are
;; — but they call `+workspace-switch' FIRST, so even run by accident they build
;; in the @Claude/@Workbench workspace, never in the one you are standing in.
(defun metsatron/claude-layout ()
  "Switch to the @Claude workspace (creating it) and (re)build it."
  (interactive)
  (+workspace-switch "@Claude" t)
  (metsatron/claude-workspace-build))

(defun metsatron/workbench-layout ()
  "Switch to the @Workbench workspace (creating it) and (re)build it."
  (interactive)
  (+workspace-switch "@Workbench" t)
  (metsatron/workbench-build))

;; Doom owns SPC TAB as the workspace prefix (SPC l is taken by list/llm/collab),
;; so the layout doors live there. SPC o w + C-c w keep the Spacemacs workbench
;; muscle memory. (Spacemacs' SPC l c became SPC TAB c.)
(map! :leader
      :desc "Layout: @Claude"    "TAB c" #'metsatron/claude-layout
      :desc "Layout: @Workbench" "TAB w" #'metsatron/workbench-layout
      :desc "Layout: @Workbench" "o w"   #'metsatron/workbench-layout)
(global-set-key (kbd "C-c w") #'metsatron/workbench-layout)

;;; ===========================================================================
;;; Org prettification (from emacs.org blk-org-look / basics / linenums)
;;; ===========================================================================
;;
;; org-modern + org-appear ship with Doom's (org +pretty), but Doom does NOT
;; enable their modes — so we own the hooks. org-modern is used for TABLES ONLY:
;; every feature that would paint headings, stars, emphasis or blocks is switched
;; OFF, because metsatron/org-apply-heading-faces and the stars toggle already
;; own those surfaces. Two painters on one glyph is how a heading flickers.
(after! org
  (setq org-hide-emphasis-markers t
        org-pretty-entities t
        org-ellipsis "…")

  ;; --- stars visibility (owned here, toggleable) ---
  (defvar metsatron/org-stars-hidden t)
  (defvar metsatron/org--hide-stars-rule '(("^\\(\\*+\\) " (1 'org-hide))))
  (defun metsatron/org--apply-stars-visibility ()
    (if metsatron/org-stars-hidden
        (progn
          (setq org-hide-leading-stars t)
          (set-face-attribute 'org-hide nil :foreground (face-background 'default nil t) :inherit nil)
          (font-lock-add-keywords nil metsatron/org--hide-stars-rule 'append))
      (setq org-hide-leading-stars nil)
      (font-lock-remove-keywords nil metsatron/org--hide-stars-rule)
      (set-face-attribute 'org-hide nil :foreground nil :inherit 'shadow))
    (font-lock-flush) (font-lock-ensure))

  ;; --- heading + document faces (owned here, NOT org-modern) ---
  (defun metsatron/org-apply-heading-faces ()
    (set-face-attribute 'org-document-title nil :inherit 'variable-pitch :weight 'bold :foreground "#ffffff" :height 173)
    (set-face-attribute 'org-document-info  nil :inherit 'variable-pitch :weight 'bold :foreground "#ffffff")
    (set-face-attribute 'org-level-1 nil :inherit 'variable-pitch :weight 'bold :height 158)
    (set-face-attribute 'org-level-2 nil :inherit 'variable-pitch :weight 'bold :height 143)
    (set-face-attribute 'org-level-3 nil :inherit 'variable-pitch :weight 'bold :height 120)
    (set-face-attribute 'org-level-4 nil :inherit 'variable-pitch :weight 'bold :height 110)
    (dolist (lv '(org-level-5 org-level-6 org-level-7 org-level-8))
      (set-face-attribute lv nil :inherit 'variable-pitch :weight 'bold :height 110)))

  (defun metsatron/org-looks ()
    (variable-pitch-mode 1)
    (dolist (f '(org-code org-verbatim org-table
                          org-block org-block-begin-line org-block-end-line
                          org-meta-line org-special-keyword org-checkbox))
      (set-face-attribute f nil :inherit 'fixed-pitch))
    (metsatron/org-apply-heading-faces)
    (metsatron/org--apply-stars-visibility))
  (add-hook 'org-mode-hook #'metsatron/org-looks)

  ;; --- tables: valign + org-modern (TABLES ONLY, all else OFF) ---
  (setq valign-fancy-bar t
        org-modern-table t
        org-modern-star nil
        org-modern-hide-stars nil
        org-modern-list nil
        org-modern-checkbox nil
        org-modern-todo nil
        org-modern-tag nil
        org-modern-priority nil
        org-modern-timestamp nil
        org-modern-block-name nil
        org-modern-keyword nil)
  (add-hook 'org-mode-hook #'valign-mode)
  (add-hook 'org-mode-hook #'org-modern-mode)

  ;; Reapply faces after any theme change (theme/org-modern can reset them).
  (advice-add 'load-theme :after
              (lambda (&rest _)
                (dolist (b (buffer-list))
                  (with-current-buffer b
                    (when (derived-mode-p 'org-mode)
                      (metsatron/org-looks))))))

  ;; --- toggle: emphasis markers + stars on/off ---
  (defun metsatron/org-toggle-pretty ()
    (interactive)
    (setq org-hide-emphasis-markers (not org-hide-emphasis-markers))
    (setq metsatron/org-stars-hidden (not metsatron/org-stars-hidden))
    (metsatron/org--apply-stars-visibility))
  (define-key org-mode-map (kbd "C-c e") #'metsatron/org-toggle-pretty)

  ;; --- basics: soft wrap, small fixed-pitch line numbers, src indentation ---
  (add-hook 'org-mode-hook
            (lambda ()
              (face-remap-add-relative 'line-number
                                       '(:family "SFMono Nerd Font Mono" :height 0.82))
              (face-remap-add-relative 'line-number-current-line
                                       '(:family "SFMono Nerd Font Mono" :height 0.82))
              (visual-line-mode 1)
              (setq-local truncate-lines nil)
              (setq org-startup-truncated nil)))
  (setq-default display-line-numbers-width-start t)
  (setq org-adapt-indentation nil
        org-src-tab-acts-natively t
        org-src-preserve-indentation t
        org-edit-src-content-indentation 0)
  (add-hook 'org-mode-hook     (lambda () (setq-local electric-indent-inhibit t)))
  (add-hook 'org-src-mode-hook (lambda () (setq-local electric-indent-inhibit t)))

  ;; --- line numbers on in org ---
  (add-hook 'org-mode-hook
            (lambda ()
              (setq-local display-line-numbers t)
              (display-line-numbers-mode 1))))

(map! :leader :desc "Org toggle pretty" "o e" #'metsatron/org-toggle-pretty)
