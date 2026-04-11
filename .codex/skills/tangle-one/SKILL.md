---
name: tangle-one
description: tangle-one - Single DotCortex Tangle
---

# tangle-one - Single DotCortex Tangle

Use this when the user wants to tangle one DotCortex org file without running a
full `make tangle`.

## Usage

- `/tangle-one <file.org>`

If no argument is given, determine the likely target from the task or ask only
if the intent is genuinely ambiguous.

## Steps

1. Validate that the target is an existing root-level DotCortex `.org` file in
   `~/DotCortex/`.
2. Run `tangle-one <file.org>` from `~/DotCortex`.
3. Re-read the relevant generated target or summarize the command evidence.
4. Report the number of tangled blocks or the key verified outcome.

## Common Examples

```bash
# Shell and terminal config
tangle-one shell.org

# Nala/Antigravity/package repo config
tangle-one nala.org

# Package manifests
tangle-one pip.org
tangle-one npm.org
tangle-one flatpak.org

# Loom control plane (Makefile and verbs)
tangle-one loom.org

# Bootstrap and system setup
tangle-one guix.org
```

## Rules

- Prefer this over `make tangle` when the task only touches one owning org file.
- Do not edit tangled output directly before or after using it.
- If the task touches multiple owning org files, use `make tangle` instead.
- Mention if the caller likely still needs `make safe-stow`, a machine-specific
  Loom stow verb, or a manager apply step after tangling.
- If the requested change looks wider than one file or alters control-plane behavior, stop and plan first.

## Notes

- `style.org` is handled specially by the existing tangle flow.
- This is especially useful for files like `shell.org`, `nala.org`,
  `flatpak.org`, `loom.org`, `pip.org`, and `npm.org`.
