---
type: capability
id: SPECKIT
title: Spec Kit integration
description: The Spec Kit extension and preset that run the simple-app workflow inside Spec Kit, and the stopgap that computes their answers until the CLI takes over.
status: draft
retired: []
---

# Spec Kit integration

The `bondstone` extension gives agents four commands and the document templates; the `bondstone` preset makes each Spec Kit spec one story, adds the expected and actual living-doc changes, and makes example-named tests a task. Behind the commands, a stopgap script applies the simple-app profile (the PROFILE capability) to the documents, Spec Kit's folders and the JUnit report, and computes findings, evidence, the phase and the next step, so the agent never computes them. Later releases move this work into the CLI and delete the stopgap.

| Rule | Checks | Severity |
| --- | --- | --- |
| `change-has-story` | A spec's front-matter names its story, or says `track: quick` | error |
| `story-before-approval` | No story starts before its PRD is approved | error |
| `change-restates-requirement` | An unfinished spec restates no requirement text | error |
| `change-plan-impact` | plan.md declares `## Expected living-doc impact` | error |
| `change-tasks-cover-examples` | tasks.md names every example the story proves, and updates the living docs | error |
| `change-living-docs` | A finished story's spec fills `## Living doc changes` | error |
| `change-proves-mismatch` | A spec proves what its story row says | warning |

## Requirements

### SPECKIT-1 Four commands
Release: V-0.0

When installed with `specify extension add`, the extension shall register exactly four commands: `speckit.bondstone.status`, `speckit.bondstone.next`, `speckit.bondstone.write` and `speckit.bondstone.check`. Claude Code installs them as skills, typed `/speckit-bondstone-status` and so on.

- SPECKIT-1.1: WHEN the extension is installed into a Spec Kit 1.2 project THEN `specify extension list` shows `bondstone` with four commands.

### SPECKIT-2 Command files
Release: V-0.0

The command files shall relay what the wrapper script prints instead of computing a status, a phase or a next step, and shall name no document type or rule. `write` shall ask the agent to write or update the document that the next step names, from its template. Each file shall tell the agent never to change `status`, `verified` or a `Verified:` line, never to run `bondstone approve` or `bondstone verify`, and never to reuse an ID.

- SPECKIT-2.1: WHEN the lint test scans the command files THEN it finds no document type or rule name, and finds every prohibition in each file.

### SPECKIT-3 Wrapper script
Release: V-0.0

The extension's wrapper script shall run the stopgap with the command's name and arguments, and exit with the stopgap's exit code.

- SPECKIT-3.1: WHEN `bondstone.sh check` runs on a project with an error THEN it exits with 1, and WHEN it gets an unknown command THEN it exits with 2.

### SPECKIT-4 Spec Kit folders are stories
Release: V-0.0

Each folder under `specs/` whose name starts with a number or a `YYYYMMDD-HHMMSS` timestamp, then a hyphen, shall be a change. Its spec is one story: the front-matter of `spec.md` names `story: ST-<n>` and `proves: [...]`, and `removes: [...]` when the story removes behavior, or says `track: quick` for a fix with no change in intended behavior. A change shall be finished when its `tasks.md` exists and every task in it is checked. Spec Kit's numbering stays independent of story numbers, and its own `FR-` and `SC-` IDs are text.

- SPECKIT-4.1: WHEN `specs/007-photo/tasks.md` has 6 checked and 5 unchecked tasks THEN the change is unfinished.
- SPECKIT-4.2: WHEN a spec names neither a story nor `track: quick` THEN `change-has-story` is reported.
- SPECKIT-4.3: WHEN a spec belongs to a story of a draft PRD THEN `story-before-approval` is reported.
- SPECKIT-4.4: WHEN a folder is named `20261030-101500-offline` THEN it is a change.

### SPECKIT-5 Analyze checks
Release: V-0.0

For an unfinished change, `check` shall report a spec that restates a sentence of a requirement it proves, a plan without `## Expected living-doc impact`, and a tasks file that does not name every example the story proves or has no living-doc task. With `--change <folder>`, it shall report only the findings in that folder; the preset's `speckit.analyze` and `speckit.implement` run it this way, and its errors block implementation.

- SPECKIT-5.1: WHEN a spec repeats SYNC-1's statement THEN `change-restates-requirement` is reported.
- SPECKIT-5.2: WHEN plan.md has no expected-impact section THEN `change-plan-impact` is reported.
- SPECKIT-5.3: WHEN a story proves SYNC-1 and tasks.md names only SYNC-1.1 THEN `change-tasks-cover-examples` names SYNC-1.2.
- SPECKIT-5.4: WHEN tasks.md has no living-doc task THEN `change-tasks-cover-examples` is reported.
- SPECKIT-5.5: WHEN `check --change specs/001-offline` runs and only another folder has errors THEN it exits with 0.

### SPECKIT-6 Living doc changes
Release: V-0.0

A finished change's spec shall record what it changed in the living docs under `## Living doc changes`, or `None: <reason>`. HTML comments do not count.

- SPECKIT-6.1: WHEN a finished spec's section holds only a comment THEN `change-living-docs` is reported, and WHEN it says `None: refactor only` THEN it is not.

### SPECKIT-7 Check report
Release: V-0.0

`check` shall print one line per finding, `<file>:<line>: <severity> <rule>: <message>`, sorted by file, line and rule, then a summary line; with `--json`, it shall print one JSON object with `schema_version`, `summary`, `findings` and `requirements` instead. It shall exit with 0 when there is no error, 1 when there is one, 2 on a usage error and 3 on an internal error. With `--staged`, it shall check the files as they are in the git index and skip evidence. Two runs on the same files shall print the same bytes.

- SPECKIT-7.1: WHEN `check` finds errors THEN it exits with 1 and prints sorted finding lines and the summary.
- SPECKIT-7.2: WHEN `check` and `status` run twice on the same files THEN each prints the same bytes.
- SPECKIT-7.3: WHEN `check --json` runs THEN it prints `schema_version`, `summary`, `findings` and `requirements`.
- SPECKIT-7.4: WHEN `check` gets an unknown option THEN it exits with 2.
- SPECKIT-7.5: WHEN a broken file is changed but not staged THEN `check --staged` exits with 0.

### SPECKIT-8 Status
Release: V-0.0

`status` shall show the current version and phase, each phase as done or with what is open, each in-scope capability with its requirement counts by evidence status, and each story of the current PRD with its status and task count. With `--json`, it shall print the same as one object.

- SPECKIT-8.1: WHEN ST-1 has a folder with one of four tasks checked THEN `status` shows phase `build V-1.0` and `ST-1 in progress (specs/001-offline: 1/4 tasks)`.

### SPECKIT-9 Next step
Release: V-0.0

`next` shall return exactly one action with a reason, the first that applies:

1. `fix`, when there are errors;
2. `run`, with Spec Kit's command for the first unfinished change in folder order: `speckit.clarify` while the spec has open clarification markers, `speckit.plan` without `plan.md`, `speckit.tasks` without `tasks.md`, otherwise `speckit.implement`;
3. `write`, `approve` or `run` for the first open document of Inception (brief, glossary, idea inbox), Shape (roadmap, architecture overview, constitution, first PRD), Foundation (constitution, runbook, walking skeleton) or Next version (the current PRD);
4. `run` with `speckit.specify` for the first ready story of the current PRD, with its ID, title and proves as arguments;
5. `write` for story rows when an in-scope requirement has no story, then `build` for a requirement still open after its stories;
6. `verify`, for a manual requirement without a `Verified:` line;
7. `write` the release checklist, `approve` it, `write` the changelog section, then `approve` shipping the version;
8. `done`.

With `--json`, it shall print the action as one object. `next` shall change no files.

- SPECKIT-9.1: WHEN there is an error THEN `next` returns `fix`.
- SPECKIT-9.2: WHEN `specs/001-offline` has no plan.md THEN `next` returns `run speckit.plan` for it.
- SPECKIT-9.3: WHEN the project is empty THEN `next` returns `write` the brief.
- SPECKIT-9.4: WHEN the PRD is approved and ST-1 is ready THEN `next` returns `run speckit.specify` for ST-1 with SYNC-1.
- SPECKIT-9.5: WHEN every story is done and every in-scope requirement passes THEN `next` returns `write plan/1.0/release.md`.
- SPECKIT-9.6: WHEN V-1.0 is shipped and PRD-1.1 is a draft THEN `next` returns `approve PRD-1.1`.
- SPECKIT-9.7: WHEN SYNC-2 is in scope and no story proves it THEN `next` returns `write` naming SYNC-2.
- SPECKIT-9.8: WHEN `next` runs twice THEN no file is added, removed or changed.

### SPECKIT-10 Pre-commit hook
Release: V-0.0

A pre-commit hook script shipped with the extension shall run `check --staged` and refuse the commit on errors. When `CLAUDE_CODE_CHILD_SESSION` is set, as Claude Code does in the shells it runs, it shall also refuse staged lines that add or remove `status: stable`, `status: deprecated`, `verified:`, a `Verified:` line or `Status: shipped`, and say that approvals are for people.

- SPECKIT-10.1: WHEN a shell where `CLAUDE_CODE_CHILD_SESSION` is set commits `status: stable` THEN the commit is refused.
- SPECKIT-10.2: WHEN the person commits the same change from their own terminal THEN the commit goes through.
- SPECKIT-10.3: WHEN a staged document has a `parse-error` THEN the commit is refused.

### SPECKIT-11 Preset
Release: V-0.0

The preset shall wrap Spec Kit's spec template with story front-matter before it and `## Living doc changes` after it; append `## Expected living-doc impact` to the plan template; append two tasks to the tasks template, example-named failing tests and the living-doc update; and append Bondstone's rules to the `speckit.specify`, `speckit.plan`, `speckit.tasks`, `speckit.analyze` and `speckit.implement` commands. It shall compose with `wrap` and `append` only, never replace.

- SPECKIT-11.1: WHEN the preset's spec template is read THEN it starts with `story:` front-matter and ends with `## Living doc changes` after `{CORE_TEMPLATE}`.
- SPECKIT-11.2: WHEN the plan and tasks templates are read THEN they hold the expected-impact section, the example-test task and the living-doc task.
- SPECKIT-11.3: WHEN the manifest is read THEN it extends exactly five commands, all by `append` or `wrap`.

### SPECKIT-12 Agent behavior
Release: V-0.0 · Check: manual

`/speckit-bondstone-next` shall do the action the next step names, after reading the documents it names, or tell the person what to approve or verify. Every extension command, run a second time on an unchanged repository, shall change no files.

- SPECKIT-12: WHEN a fresh session runs `/speckit-bondstone-next` and the action is `approve PRD-1.0` THEN the agent asks the person to approve PRD-1.0 and changes nothing.

### SPECKIT-13 Document templates
Release: V-0.0

The extension shall ship a template for every document `next` can ask to write: brief, glossary, idea inbox, roadmap, architecture overview, data model, capability spec, decision, screens, runbook, version PRD, epic, release checklist and spike note. Each template carries the front-matter its document needs and comments with its rules.

- SPECKIT-13.1: WHEN the manifest is read THEN every document `next` can write has a template file.
