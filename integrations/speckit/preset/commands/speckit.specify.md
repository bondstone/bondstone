## Bondstone: one story per spec

- This spec is exactly one story row. If the input names a story (`ST-<n>`), read that row in the version PRD or its epic under `plan/`, the capability specs in `docs/capabilities/` for the IDs it proves, and the architecture overview. Read nothing archived and no finished `specs/` folder.
- Fill the front-matter: `story: ST-<n>` and `proves: [...]` copied from the row, plus `removes: [...]` when the row has removals. For a bug fix with no change in intended behavior, use `track: quick` instead.
- Do not restate requirement text. Refer to requirements and examples by ID; in acceptance scenarios, list the example IDs covered.
- If the input names no story, run `bash .specify/extensions/bondstone/scripts/bash/bondstone.sh next` and follow it instead of inventing scope. A requirement nobody planned is an amendment to the PRD, not scope added in a spec.
- Never change `status`, `verified` or a `Verified:` line.
