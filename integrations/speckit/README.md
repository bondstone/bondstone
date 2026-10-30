# Bondstone for Spec Kit

A Spec Kit extension and preset that run the simple-app workflow: living docs that describe the product, version PRDs that change it through deltas, one story per Spec Kit spec, and evidence from example IDs in test names. A stopgap script computes every answer, so the agent never decides what the status or the next step is.

## Install

Requires Spec Kit 1.2 and Python 3.9 or later; the stopgap uses only the standard library.

```console
$ specify init --here --integration claude
$ specify extension add --dev path/to/bondstone/integrations/speckit/extension
$ specify preset add --dev path/to/bondstone/integrations/speckit/preset
$ ln -s ../../.specify/extensions/bondstone/scripts/bash/pre-commit.sh .git/hooks/pre-commit
```

Then run `/speckit-bondstone-next` and do what it says. On an empty project it asks for a brief.

## Commands

| Command | Does |
| --- | --- |
| `/speckit-bondstone-next` | Computes the one next step and does it, or asks you to approve or verify |
| `/speckit-bondstone-status` | Version, phase, evidence per capability, story progress |
| `/speckit-bondstone-write` | Writes the document the next step names, from its template |
| `/speckit-bondstone-check` | Checks docs, stories and test evidence; runs after `speckit.analyze` and before `speckit.implement` |

The same answers come from the shell: `bash .specify/extensions/bondstone/scripts/bash/bondstone.sh next|status|check [--json]`.

## The workflow in one page

```text
docs/                          living docs, kept forever
  brief.md  roadmap.md  ideas.md  glossary.md  runbook.md
  architecture/overview.md  architecture/data-model.md
  capabilities/sync.md         SYNC-2 · Release: V-1.1, examples SYNC-2.1, SYNC-2.2
  decisions/0001-*.md  ux/screens.md
plan/1.1/prd.md                deltas (ADDED, MODIFIED, REMOVED, DEFERRED, DROPPED) and story table
plan/1.1/epics/EP-4-*.md       optional
plan/1.1/release.md            release checklist, drift audit, retro
plan/archive/1.0/              shipped versions
specs/009-offline-edits/       one story: spec.md front-matter `story: ST-17`, `proves: [SYNC-2]`
```

- **Phases**, computed on every run: 0 Inception (brief), 1 Shape (roadmap, architecture, first PRD), 2 Foundation (constitution, runbook, a passing test in the JUnit report), then for every version 6 Next version (PRD approved), 3 Build (stories done, requirements passing) and 4 Release (checklist signed off, changelog, shipped); 5 Operate runs alongside.
- **Deltas:** ADDED requirements land in the capability spec as planned when the PRD is approved. MODIFIED and REMOVED land in the commit of the story that changes the code; until then the requirement carries `Pending: PRD-1.1`.
- **Story loop:** pick, load context, `speckit.specify`, `speckit.clarify` if needed, `speckit.plan` (with `## Expected living-doc impact`), `speckit.tasks` (always example-named tests and the living-doc update), `speckit.analyze` (Bondstone's checks block implement), `speckit.implement` test-first, living docs in the same commit (`## Living doc changes`), review, finish.
- **Evidence:** a test named `test_SYNC_2_1_edit_kept_after_restart` proves SYNC-2.1 when it passes in the JUnit report (`build/test-results/*.xml` by default). A requirement passes when all its examples pass.
- **Approvals** are `status: stable`, set by a person. The pre-commit hook refuses approvals committed from an agent's shell.

Configure where tests and reports live in `.specify/extensions/bondstone/bondstone-config.yml`:

```yaml
junit: [build/test-results/*.xml]
tests: [tests/**/*.py, src/**/*.test.ts]
```

`tests/fixtures/habit-app/` in this repository is a mid-build example project to try the commands on.
