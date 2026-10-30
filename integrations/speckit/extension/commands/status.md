---
description: "Show the version, phase, evidence per capability and story progress"
---

# Bondstone status

## User Input

```text
$ARGUMENTS
```

## Steps

1. Run from the repository root:

   ```bash
   bash .specify/extensions/bondstone/scripts/bash/bondstone.sh status $ARGUMENTS
   ```

2. Show the output to the person exactly as printed. Do not compute, reorder or correct any status, phase or count yourself; the script is the only source.
3. If the script exits with 2 or 3, show its error and stop.

## Never

- Never change `status`, `verified` or a `Verified:` line, and never mark a version shipped. Only the person approves, verifies or ships.
- Never run `bondstone approve` or `bondstone verify`.
- Never reuse an ID. A removed ID goes to its document's `retired` list.
