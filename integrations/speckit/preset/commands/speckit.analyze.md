## Bondstone: deterministic checks

- Run `bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check --change specs/<this feature's folder>` and show its findings.
- Its errors (a restated requirement, a missing expected-impact section, an example without a test task, no living-doc task) block `speckit.implement` until they are fixed. Your own findings above are advice.
