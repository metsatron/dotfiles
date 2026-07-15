---
name: doom-emacs
description: The DotCortex Doom Emacs environment and its claude-code-ide plugin — config lives in doom.org (tangles config.el; DOOMDIR is a dir symlink), the multi-Emacs server-socket channel traps (emacsclient hits Spacemacs; use server-name doom or the MCP bridge), how claude-code-ide runs the CLI in vterm with CLAUDE_CODE_NO_FLICKER, the alt-screen scrollback gotcha and its emulation-map fix, the keymap priority ladder, hot-loading, and Doom rebuild recovery. Load when working inside, configuring, or debugging Doom Emacs.
---

# Doom Emacs + claude-code-ide — the DotCortex editor

Load this when working inside, configuring, or debugging Mètsàtron's Doom Emacs — especially the `claude-code-ide` plugin that hosts Claude Code itself. Pairs with **emacs-live** (drive the running image; window-tree/measurement gotchas) and **elisp-craft** (elisp house style — but note that skill still describes the Spacemacs `emacs.org`→`init.el` path; for Doom, author in `doom.org` instead).

## Where the config lives (never edit tangled output)

- Doom config is authored in **`doom.org`** at repo root → tangles `all/.config/doom/{init,config,packages}.el`. Never edit the `.el`; edit `doom.org` then `tangle-one doom.org`.
- **DOOMDIR `~/.config/doom` is a directory symlink** into `all/.config/doom` (`doom -> ../DotCortex/all/.config/doom`), so a tangle is immediately live on disk — no re-stow. Restart Doom (or hot-load through the MCP bridge) to pick it up.
- `custom.el` is deliberately NOT org-owned (`custom-file` redirected to `doom-cache-dir`).
- This system uses **eglot, not lsp-mode** — the `+lsp` module flags were dropped. Never re-add `+lsp` to treemacs/sh or elsewhere.
- Launch Doom: `emacs --init-directory ~/.config/emacs`. Vanilla Emacs is plain `emacs`. Legacy Spacemacs (being retired) is `emacs --init-directory ~/.emacs.d.spacemacs`. All three coexist.

## Three Emacs can run at once — always confirm which one you inspect

- Doom (`~/.config/emacs`) and Spacemacs (`~/.emacs.d.spacemacs`) are frequently both live during the migration tail.
- There is **one default `server` socket**; whoever starts first owns it. Spacemacs grabbed it, so Doom sets `server-name "doom"` → its socket is `/run/user/UID/emacs/doom`, reached with `emacsclient -s doom --eval '…'`.
- **THE CHANNEL TRAP (cost real time 2026-07-15):** plain `emacsclient --eval` connects to whatever owns the *default* `server` socket — that was **Spacemacs, not Doom**. A reading taken that way describes the wrong image. Before trusting any emacsclient reading, fingerprint the instance: `(list (emacs-pid) user-emacs-directory (boundp 'doom-version) (boundp 'spacemacs-version))`.
- When you are running *as* claude-code-ide, the reliable channel to the Doom that hosts you is the **MCP bridge** — `mcp__ide__executeCode` (raw elisp, no shell-quoting) and `mcp__emacs-tools__*` — NOT emacsclient. Those always land in the correct Doom process.

## claude-code-ide — how it actually runs

- Runs the **real `claude` CLI in a vterm** (`claude-code-ide-terminal-backend` = `vterm`), so every DotCortex hook/skill/plugin fires exactly as in a bare terminal, and bridges Emacs↔Claude over MCP (xref, imenu, project info, flycheck exposed as tools via `claude-code-ide-emacs-tools-setup`).
- The host buffer is `*claude-code[PROJECT]*`; the project root is `(doom-project-root)`, and layouts put it in the `@Claude` perspective.
- `CLAUDE_CODE_NO_FLICKER=1` is exported in `doom.org` via `setenv` — Anthropic's virtualized-scrollback renderer. claude-code-ide *also* has a `claude-code-ide-no-flicker` var, but it only injects the env var when that var is non-nil (it is nil here); the global `setenv` is what makes NO_FLICKER load-bearing regardless of which client launches the CLI.

## GOTCHA — Claude TUI scrollback: forward the gesture, don't scroll Emacs (sealed 2026-07-15)

- The Claude TUI paints on the **alternate screen**, which writes nothing to the vterm scrollback ring. Measured: the `*claude-code*` buffer holds exactly **one screenful** (e.g. 54 lines in a 54-row window) no matter how much scrolled past, despite `vterm-max-scrollback` 100000. **The history lives ONLY inside the CLI**, in its NO_FLICKER virtualized scrollback.
- The only way to reach it is to **forward the scroll key THROUGH to the app**. `vterm-mode-map` already forwards `<prior>`/`<next>` via `vterm--self-insert` — which is why in a bare Emacs scrollback "just works" and claude-code-ide ships no scroll bindings of its own.
- **Doom breaks it:** `pixel-scroll-precision-mode` binds PageUp/PageDown and `ultra-scroll` binds the wheel, at priorities that SHADOW vterm's forwarding. The keys scroll the empty Emacs buffer; nothing reaches the CLI, so scrollback appears dead.
- **`vterm-copy-mode` is NOT the fix — and this was misdiagnosed once.** copy-mode scrolls the vterm ring, which on the alt screen is empty. A prior `doom.org` note claimed "native copy-mode scrollback" was the path and *removed* the forwarding; it was wrong and even contradicted itself two lines down ("a full-screen TUI on the alternate screen writes no ring").
- **The fix** (`metsatron/claude-scroll-forward-mode` in `doom.org`): a buffer-local minor mode forwarding `<prior>`/`<next>`/`<S-prior>`/`<S-next>`/wheel to the app, registered as an **emulation map at the front of `emulation-mode-map-alists`** — the only tier that outranks BOTH pixel-scroll (minor-mode-map-alist) and ultra-scroll (which wins from above the minor-mode maps). Enabled via `:after` advice on `claude-code-ide--configure-vterm-buffer`, scoped to Claude vterm buffers so ordinary shell vterms keep Doom's smooth-scroll. A wheel notch sends a full PageUp/Down (no finer "scroll N lines" reaches the app without vterm mouse-tracking).
- Diagnosing scroll-key shadowing: `(minor-mode-key-binding (kbd "<prior>"))` reveals the minor-mode owner; `(key-binding (kbd "<prior>"))` reveals the ultimate winner. When they differ, a higher tier (emulation/global) is winning — you must bind above it, not alongside it.

## Keymap priority ladder (highest wins) — for beating a stubborn binding

`overriding-terminal-local-map` > `overriding-local-map` > `emulation-mode-map-alists` > `minor-mode-overriding-map-alist` > char-property keymaps > `minor-mode-map-alist` > buffer-local (major-mode) map > `global-map`. To beat a *global minor mode* in one buffer, `minor-mode-overriding-map-alist` is enough; to beat something bound *above* minor modes (like ultra-scroll's wheel), you need an **emulation map**. Never try to win by binding in the major-mode map — it sits below every minor mode.

## Hot-loading a change without a restart

- Doom's tangled `config.el` loads only at startup. To exercise a change live, eval it through `mcp__ide__executeCode` (safe for reads and non-window mutations). `defvar`/`define-minor-mode` do NOT re-set an already-bound variable — `setq` or re-eval explicitly when hot-patching, or new code silently keeps the old value.
- Verify the fix in the running image *before* sealing "this works" into source as fact. But the ultimate proof for TUI scrollback is a human keypress (only the user sees the CLI scroll) — resolve the keymap live, then have the user press the key.
- **THE DANGER:** your CLI lives in a vterm INSIDE Doom. Restarting Doom, or window surgery (spawn/kill terminals, `set-window-configuration`) around your host buffer, SIGHUPs your own session. Read freely; mutate carefully; never restart Doom or churn windows around yourself. (Full detail in emacs-live.)

## Rebuilding Doom (recovery)

- Full procedure: `doom.org → "Rebuilding Doom (recovery procedure)"`.
- The `doom sync` "hour-long spin" is almost always interactive prompts fed the wrong answer, not a hang. Robust answer stream: `while true; do printf 'y\n3\n2\n'; sleep 0.05; done | doom sync` (each prompt self-selects a valid, safe option; Abort is never fed).
- Recurring "How to proceed? (Discard changes)" during sync = one dirty straight submodule (`with-gnu-utils` inside the `general.el` straight repo). `reset --hard`/`clean` cannot fix it (they do not recurse submodules). Neutralize locally: `git -C ~/.config/emacs/.local/straight/repos/general.el update-index --assume-unchanged with-gnu-utils`.
