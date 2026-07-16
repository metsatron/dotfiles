---
name: elisp-craft
description: Write and adapt Emacs Lisp for DotCortex — emacs-spacemacs.org block conventions, elisp best practices (defgroup/defcustom/defface, user-error, shell-quote-argument, compile), respectful upstream adaptation with credit, and batch testing with the lexical-binding gotcha.
---

# Elisp Craft — Writing and Adapting Emacs Lisp for DotCortex

Load this before writing ANY Emacs Lisp: new config blocks in `emacs-spacemacs.org`, interactive commands, or adaptations of upstream elisp. The standards below are house style, adopted from Josep Bigorra's heks-emacs (https://codeberg.org/jjba23/heks-emacs) — the project whose maak runner sparked loom.

## DotCortex Emacs config conventions

- **Spacemacs elisp is authored in `emacs-spacemacs.org`** as named noweb blocks (`#+NAME: blk-<topic>`), referenced from the `dotspacemacs/user-config` assembly block that tangles to `all/.spacemacs.d.claude/init.el`. Never edit `init.el` directly.
- Adding a Spacemacs block = two edits: the `** heading` with `#+NAME: blk-X` source block, AND `` in the user-config assembly list. Then `tangle-one emacs-spacemacs.org`.
- **Keybindings**: check what is taken first (`grep -n 'set-leader-keys\|global-set-key' emacs-spacemacs.org`). User commands get a `SPC o <letter>` Spacemacs leader binding (guarded with `(when (fboundp 'spacemacs/set-leader-keys) …)`) plus a `C-c <prefix> <letter>` global binding. Match the file's `global-set-key (kbd …)` idiom.
- **Colemak-NEIO law applies**: never build h/j/k/l movement contracts; `n/e/i/o` is the directional home row. See CLAUDE.md rule 18 before binding any motion keys.
- The tangled `init.el` carries a `lexical-binding: t` cookie — closures over `let*` bindings are safe in the real load, but see the testing gotcha below.

## Elisp craft checklist (apply to every definition)

1. **`defgroup`/`defcustom`/`defface` instead of hardcoded values** — paddings, thresholds, and appearance are customizable; faces `:inherit` theme faces (e.g. `font-lock-comment-face`), never name literal colors.
2. **`--` naming for private helpers** (`foo--parse`, `foo--binary`) — the public API surface stays visible in every call site.
3. **`user-error` for expected failures** ("tool not found", "nothing to select") — polite minibuffer message, no backtrace. Reserve `error` for genuine bugs.
4. **`shell-quote-argument` when building shell commands** — every fragment, even ones that look safe.
5. **Prefer `compile` for running external tasks** — free output buffer, `g` re-runs, error navigation, no bespoke process-filter code.
6. **Docstring every `defun`/`defvar`/`defface`** — first line a complete sentence; document argument conventions and side effects. `C-h f` should teach.
7. **Completion UX**: attach descriptions via `completion-extra-properties` + `:annotation-function`, aligning columns with `(propertize " " 'display '(space :align-to N))` computed from the longest candidate.
8. **Confirm destructive actions**: DotCortex verbs ending in `!` are destructive by convention — `yes-or-no-p` before running one on the user's behalf.

## Adapting upstream code respectfully

- **Read the entire upstream source before adapting.** Never port from memory or from a summary.
- **Credit twice**: in the org prose (link, author, what his/her design contributed) AND in a comment header in the code block (URL + author).
- **State what was kept and what changed, and why** — e.g. "kept the annotation-function alignment technique; replaced static file parsing with live `loom` output so the picker never drifts."
- **Prefer live truth over ported parsers**: if the local system can report its own state (like bare `loom` listing verbs with descriptions), query it instead of porting a parser for a file format the fork does not share.
- Reference implementation: `blk-loom` in `emacs-spacemacs.org` (loom-run-task, adapted from heks-emacs `maak-run-task`).

## Verifying elisp without opening Emacs

Batch-test against the real tangled output (Guix emacs lives at `~/.guix-extra-profiles/core/core/bin/emacs` if `emacs` is not on PATH):

- **Syntax/parens of the assembled file**: `emacs --batch --eval '(with-temp-buffer (insert-file-contents "all/.spacemacs.d.claude/init.el") (emacs-lisp-mode) (check-parens))'`
- **Eval a region and exercise the functions**: extract the block from `init.el` between known markers and `eval-region` it, then call the functions and `princ` results.
- **GOTCHA — lexical binding**: `eval-region` in a temp buffer defaults to *dynamic* binding regardless of the file's cookie; closures will fail with `void-variable` on captured lets. `(setq-local lexical-binding t)` in the temp buffer before `eval-region` to match real load conditions. A `:dynbind` tag in a printed closure is the tell.
- Strip text properties with `substring-no-properties` before asserting on annotation output.
