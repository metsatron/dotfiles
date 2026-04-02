# verify - Tool Presence And Help

Use this when the user wants to confirm a tool exists here and see how it is invoked.

## Steps

1. Try `<tool> --help`.
2. If that fails, try `<tool> help`.
3. If help output is unavailable, run `command -v <tool>`.
4. Report the resolved path and the first useful help lines or the failure.

## Rules

- prefer this for tool discovery, not for change verification
- use `.opencode/commands/handoff-verify.md` when verifying completed work
- report when a command exists but has no useful help output
- do not pretend a tool is missing until `command -v` also fails
