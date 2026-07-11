---
name: verify
description: Tool Presence And Help
---

# Tool Presence And Help

Use this when you need to confirm a tool exists and see how it is invoked.

## Steps

1. Try `<tool> --help`.
2. If that fails, try `<tool> help`.
3. If help output is unavailable, run `command -v <tool>`.
4. Report the resolved path and the first useful help lines or the failure.

## Rules

- Prefer this for tool discovery, not for change verification.
- Keep the report compact.
