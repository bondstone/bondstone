---
description: "Write or update the document the next step names"
---

# Bondstone write

## User Input

```text
$ARGUMENTS
```

## Steps

1. If the input names no document, run `bash .specify/extensions/bondstone/scripts/bash/bondstone.sh next --json` and use its `doc` and `path`. If the action is not `write` or `fix`, report it and stop.
2. Read the template `.specify/extensions/bondstone/templates/<doc>.md` when it exists, and follow its structure, front-matter and comments.
3. Read only what the document needs: the living docs it refers to and the active change. Interview the person for facts you do not have; never invent product decisions.
4. Write the document at `path` with `status: draft`, or update the existing one in place. Keep IDs stable; give new items the next free number.
5. Run `bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check` and fix the errors in the file you wrote.
6. Tell the person what is ready for their review and approval. Do not approve it.

## Never

- Never change `status`, `verified` or a `Verified:` line, and never mark a version shipped. Only the person approves, verifies or ships.
- Never run `bondstone approve` or `bondstone verify`.
- Never reuse an ID. A removed ID goes to its document's `retired` list.
