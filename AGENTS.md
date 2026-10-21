# Working on Bondstone

Bondstone is a deterministic CLI, with a Spec Kit extension and preset, that checks linked Markdown documents and test evidence and computes a project's next step. This repository follows Bondstone's own simple-app profile, so the documents below are the source of truth.

## Where things are

- `docs/brief.md`: problem, goals and releases. Its `release` field names the current release.
- `docs/architecture.md`: components (`COMP-…`), the code each one owns under `Paths:`, and the decisions behind them.
- `docs/spec/<capability>.md`: the living spec, one per capability. Each requirement (`CHECK-3`) states one behavior and has an example.
- `docs/decisions/`: decision records (`ADR-…`).
- `CHANGELOG.md`: one section per release.
- `.bondstone/rules.yml`: Bondstone's configuration for this repository.

## How to work

1. Once release 0.0 is installed, start with `/speckit-bondstone-next`. It names one action: do that action and nothing else. From release 0.2, `bondstone context --brief` and `bondstone context <ID>` load what the action needs.
2. Read the spec of the capability you work on, and check that its requirements are in the current release.
3. Change the spec, the tests and the code in the same commit. If behavior changes, the spec changes.
4. Name every test that proves a requirement after it: `test_CHECK_3_json_is_one_object`. Console examples in the specs run as tests through `tests/conftest.py`.
5. For three or more open requirements in one capability, use a Spec Kit change: run `/speckit-specify`, list the IDs under `## Spec changes` in its `spec.md` (`Implements:` for requirements built unchanged, `Adds:`, `Changes:`, `Removes:`), then run `/speckit-plan`, `/speckit-tasks` and `/speckit-implement`. For one or two, skip Spec Kit.
6. A new requirement takes the next free number in its spec, counting the IDs in the front-matter `retired` list and the `Adds:` lines of unfinished changes (from 0.2: `bondstone id next <capability>`). When you remove a requirement, add its ID to `retired`. Never reuse an ID.
7. Put new code under some component's `Paths`. If no component fits, ask before adding one.
8. If `next` named the wrong step, say so, so that the person can log it.

## Never

- Change `status` or `verified` in front-matter, or a `Verified:` line. New documents start as `draft`, decisions as `proposed`. The pre-commit hook refuses these changes from your shell.
- Run `bondstone approve` or `bondstone verify`. Tell the person what is ready for approval.
- Change `.bondstone/rules.yml` unless asked.
- Commit with `--no-verify`.

## Commands

```sh
uv run pytest --junitxml=build/test-results/junit.xml
uv run ruff check && uv run ruff format --check
uv run bondstone check    # from release 0.1; before that, /speckit-bondstone-check
```
