# Working on Bondstone

Bondstone is a deterministic CLI, with a Spec Kit extension and preset, that checks linked Markdown documents and test evidence and computes a project's next step. This repository follows Bondstone's own simple-app profile, so the documents below are the source of truth. Nothing is built yet: release 0.0 builds the Spec Kit extension.

## Where things are

- `docs/brief.md`: problem, goals and releases. Its `release` field names the current release.
- `docs/architecture.md`: concepts, components and the decisions behind them.
- `docs/spec/<capability>.md`: one living spec per capability, written when its release starts. Each requirement (`SPECKIT-3`) states one behavior and has an example.
- `docs/decisions/`: decision records (`ADR-…`).

The documents in `docs/` follow Open Knowledge Format 0.2: keep `type`, `id`, `title`, `description` and `status` in their front-matter.

## How to work

- Change a spec, its tests and its code in the same commit. If behavior changes, the spec changes.
- Name every test that proves a requirement after it: `test_SPECKIT_3_passes_exit_code_through`.

## Never

- Change `status` or `verified` in front-matter, or a `Verified:` line. New documents start as `draft`; tell the person what is ready for approval.
- Reuse an ID. A removed requirement's ID goes to its spec's `retired` list.
- Commit with `--no-verify`.
