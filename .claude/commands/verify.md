Verify a tool exists and show its API.

```bash
$ARGUMENTS --help 2>/dev/null || $ARGUMENTS help 2>/dev/null || which $ARGUMENTS 2>/dev/null || echo "Not found: $ARGUMENTS"
```

Report: tool location and first 30 lines of help output. No commentary.
