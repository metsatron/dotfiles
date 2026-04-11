---
name: full-rebuild-t480s
description: full-rebuild-t480s - Full Rebuild For T480s
---

# full-rebuild-t480s - Full Rebuild For T480s

Use this when the user wants a full tangle and stow rebuild for the T480s.

## Steps

1. Confirm this is not the first stow on a fresh machine.
2. From `~/DotCortex`, prefer:

```bash
loom all
loom stow:t480s
```

3. If Loom is unavailable, fall back to:

```bash
make tangle
STOW_PKGS='all linux debian devuan t480s' make safe-stow
```

4. Report errors, changed files, and the exact rebuild path used.

## Rules

- use `make safe-stow` rather than plain `stow`
- treat this as a full rebuild, not a one-file fast path
- if the task only changed one owning org file, consider `tangle-one` plus machine stow instead
- do not claim success without fresh command evidence
