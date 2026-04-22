# Tangle a single org file

Tangle a single DotCortex org file without running a full `make tangle`.

## Usage

`/tangle-one <file.org>`

If no argument is given, ask which org file to tangle.

## Steps

1. Validate the argument is an existing `.org` file at the DotCortex repo root (`~/DotCortex/*.org`).
2. Run: `tangle-one <file.org>` from `~/DotCortex`.
3. Report the number of tangled blocks from the output.

## Notes

- `style.org` is handled specially (runs `loom-style` block first).
- For most org files (shell.org, pip.org, npm.org, cargo.org, flatpak.org, loom.org, etc.) this works perfectly.
