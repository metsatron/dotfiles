---
name: emacs-live
description: Drive and inspect the user's RUNNING Emacs over emacsclient — live faces, window geometry, variable values, package APIs. Load before claiming anything about Emacs' current state. Carries the hard-won gotchas: window-list hides internal windows, delete-other-windows ignores side windows, font-at needs a displayed window, and window surgery around your own host buffer will SIGHUP your session.
---

# Emacs Live — Driving the Running Emacs over emacsclient

`emacsclient --eval` is a live REPL into the user's actual Emacs process. It is the editor's equivalent of a browser's inspect tool: read real state instead of guessing at it from files. Load this skill before making ANY claim about what Emacs is currently doing.

## Prerequisite

`dotspacemacs-enable-server t` is set in `emacs-spacemacs.org`, so the server comes up at startup. Socket lands in `$XDG_RUNTIME_DIR/emacs/server`.

```bash
ls /run/user/$(id -u)/emacs/          # socket present?
emacsclient --eval '(emacs-version)'  # channel alive?
```

If unreachable, the server is not running. Ask the user to `M-x server-start` — it takes effect immediately, no restart. Do not assume; `pgrep emacs` proves a process exists, not a server.

## THE PRIME LAW: observe, never infer

Config on disk is a **claim about** the running image, not a fact. The entire value of this channel is that it ends guessing.

- Never say "the font will be X" — measure it.
- Never say "the variable is set" — read it.
- **If your reading of the running image disagrees with the config, THAT disagreement is the finding.** Stop and reconcile it; never note it and reason past it.
- Never write a causal story into source or a commit message unless you observed the cause. Inventing a plausible mechanism ("a mistyped keybinding did it") when the real one was different is worse than saying "unknown" — it seals a lie into the record.

## THE DANGER: you are probably running INSIDE this Emacs

When invoked from `claude-code-ide` or `claude-code`, **your own CLI process lives on a pty attached to a vterm buffer in that frame.** Window surgery around it hangs up your own terminal.

Observed 2026-07-14: spawning test vterms, killing them, and calling `set-window-configuration` produced **SIGHUP → `Claude exited with code 129`**. The session died mid-experiment.

**Rule: read freely, mutate carefully, and never spawn/kill terminal buffers or restore window configurations around the buffer hosting you.** Destructive terminal experiments belong in a separate frame or an `emacs --batch`, never in the user's live workspace. Before any mutation, ask: *if this goes wrong, does it take my own session with it?*

## Shell quoting

`emacsclient --eval` takes one elisp string, usually inside a single-quoted shell string — where you cannot type `'`.

- Write `(quote foo)` and `(function foo)`, never `'foo` / `#'foo`.
- For anything long, write the elisp to a file and `(load-file "…")` it.
- Wrap risky forms in `condition-case` and return the error text — otherwise a failure prints a bare `*ERROR*` with no context and you lose the diagnosis.

## Measurement gotchas — every one of these produced a false reading

- **`font-at` needs a DISPLAYED window and a real glyph.** It returns nil on a hidden buffer or at an empty position. Pass the window explicitly — `(font-at POS WIN)` — and `re-search-forward` to an actual character first. A nil result is a measurement artifact, not "no font".
- **XLFD pixel size ≠ visible glyph height.** `-PfEd-MesloLGS Nerd Font Mono-…-14-…` renders an **11px** glyph. The XLFD number is the em box. Measure the glyph.
- **`face-remap-add-relative` runs once, at buffer creation, via the mode hook.** Existing buffers never pick up a changed hook. A buffer that predates your edit shows the old value forever — that is not a failed change, and re-running the hook won't fix a live buffer you didn't recreate.
- **Never measure a wedged buffer.** A vterm that has been through window-tree corruption may silently fail to execute what you send. Confirm your input actually ran (read the buffer tail) *before* reading a number off it. A stale buffer reporting "54 lines" nearly got an innocent feature ripped out.
- **`process-live-p` returns a memq tail** — `(run open listen connect stop)` — not `t`. Truthy, but don't misread it as data.
- **A visible `*helm mini*` window is not an active recursive edit.** If `emacsclient --eval` returns at all, Emacs is not blocked in the minibuffer.

## Window-tree gotchas — the sharpest edges in Emacs

- **`window-list` returns only LIVE windows.** Side-window state also lives on **internal parent** windows, which it never returns. To inspect or repair a corrupt tree you must walk it fully: recurse `window-child` / `window-next-sibling` from `(frame-root-window)`. Two repair attempts failed because they only touched leaves.
- **`delete-other-windows` does NOT delete side windows.** Treemacs is a side window; `claude-code-ide` stamps its window with `no-delete-other-windows`. A layout function that "resets" with a plain `delete-other-windows` **does not start from a blank frame** — it builds on top of the survivors. That is how you get duplicate Treemacs panes, a Claude buffer displaced into Treemacs' left slot, and finally a frame with no ordinary window in it at all.
- Bind **`ignore-window-parameters` to `t`** to make `delete-other-windows` actually obey.
- **`window-side` cannot be cleared on a live window alone** — clear it on the internal parents too, or Emacs signals `Window X has not same side left as its parent`.
- Save a rescue config **before** any window mutation: `(setq my--rescue (current-window-configuration))`. But see THE DANGER — restoring a config can itself hang up a hosted terminal.

## Discovering a package's real API (instead of guessing function names)

```elisp
(let (r) (mapatoms (lambda (s)
  (when (and (fboundp s) (commandp s) (string-prefix-p "claude-code-ide" (symbol-name s)))
    (push (symbol-name s) r)))) (sort r (function string<)))
```

- `symbol-function` on a byte-compiled defun returns unreadable bytecode. Read the real source from `~/.emacs.d.spacemacs/elpa/<ver>/develop/<pkg>/<pkg>.el`.
- Confirm a symbol is real before trusting it: `(boundp 'foo)`, `(fboundp 'foo)`.
- **Verify a font in Emacs' own view, not just `fc-list`**: `(member "X" (font-family-list))`.

## Safe read-only starters

```bash
emacsclient --eval '(mapcar (lambda (w) (list (buffer-name (window-buffer w)) (window-body-width w) (window-parameter w (quote window-side)))) (window-list))'
emacsclient --eval '(with-current-buffer "BUF" (format "%S" face-remapping-alist))'
emacsclient --eval '(list (cons "persp" (safe-persp-name (get-frame-persp))) (cons "layouts" (persp-names)))'
```

## Applying a config change without restarting

The tangled `init.el` only loads at startup. To exercise a change live:

1. `tangle-one emacs-spacemacs.org`
2. Extract the block from `init.el` — it is indented inside `dotspacemacs/user-config`, so strip the leading two spaces.
3. `(load-file "…")` it.

**`defvar` does NOT re-set an already-bound variable.** When hot-patching, `setq` it explicitly or you will load new code that quietly keeps the old value.

## Recovering a broken window tree

```elisp
(letrec ((clear (lambda (w)
                  (set-window-parameter w 'window-side nil)
                  (set-window-parameter w 'window-slot nil)
                  (set-window-parameter w 'no-delete-other-windows nil)
                  (let ((c (window-child w)))
                    (while c (funcall clear c) (setq c (window-next-sibling c)))))))
  (funcall clear (frame-root-window)))
(let ((ignore-window-parameters t)) (delete-other-windows))
```

Walks internal nodes (which `window-list` hides), strips the side parameters, then collapses to one ordinary window. This is the escape hatch when `window-toggle-side-windows` reports `No side windows state found` — i.e. when Emacs' own bookkeeping has diverged from the parameters on the windows.

## Terminal facts worth not rediscovering

- The Claude CLI TUI runs on the **alternate screen** (`\e[?1049h`). By terminal convention the alt screen writes **nothing** to the scrollback ring. The Claude buffer therefore holds exactly one screenful, and `vterm-max-scrollback` cannot change that — the ring never receives the lines. Not a vterm bug, not a `claude-code-ide` bug, not fixable from Emacs. The only lever is `CLAUDE_CODE_NO_FLICKER=1` (Anthropic's virtualized-scrollback renderer), set in `emacs-spacemacs.org` and `emacs-doom.org`.
- `claude-code-ide`'s anti-flicker option installs a **global** `:around` advice on `vterm--filter`. It looks like a prime suspect for vterm misbehaviour and **is not** — a fresh vterm retains full scrollback with it active (measured: 304 lines after `seq 1 300`, advice on and off). Do not blame it without an A/B on a *fresh* buffer.
