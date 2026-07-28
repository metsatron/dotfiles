;; -*- no-byte-compile: t; -*-
;;; $DOOMDIR/packages.el

;; To install a package with Doom you must declare them here and run 'doom sync'
;; on the command line, then restart Emacs for the changes to take effect -- or


;; To install SOME-PACKAGE from MELPA, ELPA or emacsmirror:
;; (package! some-package)

;; To install a package directly from a remote git repo, you must specify a
;; `:recipe'. You'll find documentation on what `:recipe' accepts here:
;; https://github.com/radian-software/straight.el#the-recipe-format
;; (package! another-package
;;   :recipe (:host github :repo "username/repo"))

;; If the package you are trying to install does not contain a PACKAGENAME.el
;; file, or is located in a subdirectory of the repo, you'll need to specify
;; `:files' in the `:recipe':
;; (package! this-package
;;   :recipe (:host github :repo "username/repo"
;;            :files ("some-file.el" "src/lisp/*.el")))

;; If you'd like to disable a package included with Doom, you can do so here
;; with the `:disable' property:
;; (package! builtin-package :disable t)

;; You can override the recipe of a built in package without having to specify
;; all the properties for `:recipe'. These will inherit the rest of its recipe
;; from Doom or MELPA/ELPA/Emacsmirror:
;; (package! builtin-package :recipe (:nonrecursive t))
;; (package! builtin-package-2 :recipe (:repo "myfork/package"))

;; Specify a `:branch' to install a package from a particular branch or tag.
;; This is required for some packages whose default branch isn't 'master' (which
;; our package manager can't deal with; see radian-software/straight.el#279)
;; (package! builtin-package :recipe (:branch "develop"))

;; Use `:pin' to specify a particular commit to install.
;; (package! builtin-package :pin "1a2b3c4d5e")


;; Doom's packages are pinned to a specific commit and updated from release to
;; release. The `unpin!' macro allows you to unpin single packages...
;; (unpin! pinned-package)
;; ...or multiple packages
;; (unpin! pinned-package another-pinned-package)
;; ...Or *all* packages (NOT RECOMMENDED; will likely break things)
;; (unpin! t)

;;; --- Migration additions ---------------------------------------------------

;; Claude Code inside Doom — the harness-preserving default (Phase 2 of the
;; Spacemacs->Doom migration). Runs the real `claude' CLI in a vterm buffer AND
;; bridges Emacs to it over MCP. Of emacs-spacemacs.org's three clients, ONLY this one is
;; ported: agent-shell (ACP; harness inert) and the thin claude-code wrapper are
;; deliberately deferred.
(package! claude-code-ide
  :recipe (:host github :repo "manzaltu/claude-code-ide.el"))

;; Codex inside Doom — the Codex-shaped counterpart to claude-code-ide. Talks to
;; `codex app-server' (renders native Emacs buffers: diff-mode patches, clickable
;; file refs, in-buffer approvals) instead of wrapping the TUI in vterm. Not on
;; MELPA; github-only. transient (its one dep) already ships with Doom via magit.
(package! codex-ide
  :recipe (:host github :repo "dgillis/emacs-codex-ide"))

;; Pi inside Doom — Emacs frontend for the Pi CLI (dnouri/pi-coding-agent). Runs
;; `pi --mode rpc' as a subprocess and renders a chat buffer (tree-sitter Markdown)
;; plus a separate prompt buffer, instead of wrapping the TUI in vterm. On MELPA,
;; so no :recipe needed.
(package! pi-coding-agent)

;; Org prettification (Phase 4). org-modern + org-appear already ship with Doom's
;; (org +pretty) flag, so only valign is added here. valign pixel-aligns table
;; columns in variable-pitch org buffers. (mixed-pitch from emacs-spacemacs.org is NOT
;; ported: it was declared but never wired — org-looks does variable-pitch
;; manually.)
(package! valign)

;; Propagates buffer-local environment variables (e.g. from `direnv') into
;; indirect/child buffers, so a direnv-derived PATH/env reaches subprocesses
;; spawned from them. Ported from emacs-spacemacs.org's additional-packages.
(package! inheritenv)
