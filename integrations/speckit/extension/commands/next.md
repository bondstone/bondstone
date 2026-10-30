---
description: "Do the one next step Bondstone computes"
---

# Bondstone next

## User Input

```text
$ARGUMENTS
```

## Steps

1. Run from the repository root:

   ```bash
   bash .specify/extensions/bondstone/scripts/bash/bondstone.sh next --json
   ```

2. Tell the person the action and its reason in one or two sentences, as printed.
3. Do exactly that one action, and nothing after it:
   - `fix`: open the file and line named, fix what the finding says, then run `bondstone.sh check` and report.
   - `run`: run the Spec Kit command named in `command`, passing `args` when given. For a `change`, work in that folder only.
   - `write`: do what `/speckit.bondstone.write` does for the `doc` and `path` named.
   - `build`: do the work the reason names, test-first.
   - `approve`: ask the person to review the document at `path` and approve it themselves. Change nothing.
   - `verify`: ask the person to check the requirement by hand and record it themselves. Change nothing.
   - `done`: say so.
4. Before acting, read the documents the action names, and only living docs plus the one active change. Do not read archived plans or finished Spec Kit folders.
5. Do not choose a different step, even if another looks more useful. If you think the step is wrong, say why and stop.
6. Running this command again on an unchanged repository must change nothing.

## Never

- Never change `status`, `verified` or a `Verified:` line, and never mark a version shipped. Only the person approves, verifies or ships.
- Never run `bondstone approve` or `bondstone verify`.
- Never reuse an ID. A removed ID goes to its document's `retired` list.
