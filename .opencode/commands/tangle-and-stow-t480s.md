# tangle-and-stow-t480s - Single-Source Apply For T480s

Use this when one owning DotCortex org file should be tangled and applied to the T480s overlays.

## Steps

1. Confirm the target is an existing root-level `.org` file in `~/DotCortex`.
2. Run:

```bash
tangle-one <file.org>
loom stow:t480s
```

3. If Loom is unavailable, fall back to:

```bash
tangle-one <file.org>
STOW_PKGS='all linux debian devuan t480s' make safe-stow
```

4. Re-read the relevant generated output or summarize the command evidence.

## Rules

- use `make tangle` instead when multiple owning org files changed
- use `make tangle` instead when the task changes `loom.org` or other control-plane behavior
- mention whether package apply commands are still needed after stow
- do not edit overlay output directly before or after this flow
