# Working on Bondstone

Bondstone is a deterministic CLI, with a Spec Kit extension and preset, that checks linked Markdown documents and test evidence and computes a project's next step. This repository follows Bondstone's own simple-app workflow (ADR-0008), so the documents below are the source of truth. Version 0.0 is the Spec Kit extension with a stopgap behind it; the CLI comes in 0.1.

## Where things are

- Living docs in `docs/`: `brief.md`, `roadmap.md` (versions; the first one not shipped is current), `ideas.md`, `glossary.md`, `architecture/overview.md`, `capabilities/<cap>.md` and `decisions/`.
- Capability specs are the only home of requirements. Each requirement (`SPECKIT-3`) states one behavior, carries `Release:` and has examples with scoped IDs (`SPECKIT-3.1`).
- Change docs in `plan/<version>/`: the version PRD with its deltas and story table. Spec Kit folders in `specs/` are one story each.
- `integrations/speckit/`: the extension (commands, templates, the stopgap and the pre-commit hook) and the preset.

The documents follow Open Knowledge Format 0.2: keep `type`, `id`, `title`, `description` and `status` in their front-matter.

## How to work

- Start from `python3 integrations/speckit/extension/scripts/python/bondstone_stopgap.py next`, or `/speckit-bondstone-next` in a Spec Kit project.
- Change a capability spec, its tests and its code in the same commit. If behavior changes, the spec changes.
- Name every test after the example it proves: `test_SPECKIT_3_1_wrapper_passes_exit_code`.
- Run `python3 -m pytest --junitxml=build/test-results/junit.xml`, then the stopgap's `check`.

## Never

- Change `status` or `verified` in front-matter, a `Verified:` line, or a version's `Status: shipped`. New documents start as `draft`; tell the person what is ready for approval.
- Reuse an ID. A removed requirement's or example's ID goes to its spec's `retired` list.
- Commit with `--no-verify`.
