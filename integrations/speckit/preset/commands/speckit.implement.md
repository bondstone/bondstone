## Bondstone: test-first, living docs in the same commit

- Before starting, run `bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check --change specs/<this feature's folder>`; do not implement while it reports errors.
- Write the example-named tests first and see them fail, then implement until they pass. Make the test runner write its JUnit report where Bondstone reads it (`build/test-results/`).
- In the same commit as the code and tests, update the living docs and record each change in the spec's `## Living doc changes`, reconciled against plan.md's expected impact: apply this story's MODIFIED and REMOVED deltas and clear their `Pending:` markers, move removed IDs to `retired`, add an ADR for each hard choice, merge the feature's data model and contracts into `docs/architecture/`, update the glossary and screens if touched, and add a changelog fragment.
- If a requirement turns out wrong, stop and propose a MODIFIED delta to the owner; do not change its meaning on your own.
- Never change `status`, `verified` or a `Verified:` line. The owner approves the living-doc diff in the pull request.
