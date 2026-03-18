# Tangle a single org file

Tangle a single DotCortex org file without running a full `make tangle`.

## Usage

`/tangle-one <file.org>`

If no argument is given, ask which org file to tangle.

## Steps

1. Validate the argument is an existing `.org` file at the DotCortex repo root (`~/DotCortex/*.org`).
2. Run the single-file tangle:

```bash
emacs --batch -Q \
  --eval "(setq create-lockfiles nil make-backup-files nil auto-save-default nil backup-inhibited t vc-make-backup-files nil)" \
  --eval "(require 'ob-tangle)" \
  --eval "(setq org-confirm-babel-evaluate nil)" \
  --eval "(with-current-buffer (find-file-noselect \"$FILE\") (org-mode) (org-babel-tangle) (kill-buffer))"
```

Where `$FILE` is the org file name (e.g. `shell.org`). Run this from `~/DotCortex`.

3. Report the number of tangled blocks from the emacs output.

## Notes

- This does NOT handle `style.org` specially (no `loom-style` delegation). For style.org, use `make tangle` instead.
- This does NOT run loom-style bootstrap (`lc/batch-boot-if-needed`). If org blocks use `lc/*` dynamic tangle paths, use `make tangle` instead.
- For most org files (shell.org, pip.org, npm.org, cargo.org, flatpak.org, loom.org, etc.) this works perfectly.
