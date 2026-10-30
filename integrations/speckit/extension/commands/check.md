---
description: "Check docs, stories and test evidence against the simple-app rules"
---

# Bondstone check

## User Input

```text
$ARGUMENTS
```

## Steps

1. Run from the repository root. When this runs as a hook of `speckit.analyze` or `speckit.implement`, pass the active feature folder as `--change specs/<folder>`.

   ```bash
   bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check $ARGUMENTS
   ```

2. Show the findings exactly as printed.
3. If the exit code is 1, there are errors: say so plainly. When this runs before `speckit.implement`, stop: implementation must not start until the errors are fixed. Do not fix them unasked unless the person or the next step asked for it.
4. Warnings are advice; mention them and continue.
5. Exit code 2 is a usage error and 3 an internal error: show the message and stop.

## Never

- Never change `status`, `verified` or a `Verified:` line, and never mark a version shipped. Only the person approves, verifies or ships.
- Never run `bondstone approve` or `bondstone verify`.
- Never reuse an ID. A removed ID goes to its document's `retired` list.
