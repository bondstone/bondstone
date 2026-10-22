---
type: spec
id: SPECKIT
title: Spec Kit integration
description: The Spec Kit extension and preset that let agents drive Bondstone from inside Spec Kit, and the stopgap that computes their answers until the CLI takes over.
status: draft
components: [COMP-SPECKIT]
fixture: speckit-project
---

# Spec Kit integration

The `bondstone` extension gives agents four commands, and the `bondstone` preset adds the `## Spec changes` section and test naming to Spec Kit. Behind the commands, a stopgap script reads the simple-app documents and the JUnit report, applies the profile's rules, and computes each requirement's status, the stage and the next step, so the agent never computes them. Release 0.1 moves the checks into `bondstone check`; release 0.2 moves the rest into the CLI and deletes the stopgap.

## Requirements

### SPECKIT-1 Four commands

When installed with `specify extension add`, the extension shall register exactly four commands: `speckit.bondstone.status`, `speckit.bondstone.next`, `speckit.bondstone.write` and `speckit.bondstone.check`. Claude Code installs them as skills, typed `/speckit-bondstone-status` and so on.

- WHEN the extension is installed into a Spec Kit 1.2 project THEN `specify extension list` shows `bondstone` with four commands.

### SPECKIT-2 Command files

The command files shall relay what the wrapper script prints instead of computing a status, a stage or a next step, and shall name no document type or rule. `write` shall ask the agent to write or update the document that the next step names. Each file shall tell the agent never to change `status`, `verified` or a `Verified:` line, never to run `bondstone approve` or `bondstone verify`, and never to reuse an ID.

- WHEN the lint test scans the command files THEN it finds no document type or rule name, and finds every prohibition in each file.

### SPECKIT-3 Wrapper script

The extension's wrapper script shall run the stopgap with the command's name and arguments, and exit with the stopgap's exit code.

```console
$ bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check
errors: 0 · warnings: 0
```

### SPECKIT-4 Documents

The stopgap shall read these documents. Each is a Markdown file whose front-matter follows Open Knowledge Format 0.2 and has `type`, `id`, `title`, `description` and `status`; `status` is `draft`, `stable` or `deprecated`.

| Type | ID | Path |
| --- | --- | --- |
| `brief` | `BRIEF` | `docs/brief.md` |
| `architecture` | `ARCH` | `docs/architecture.md` |
| `spec` | its capability prefix, such as `SYNC` | `docs/spec/*.md` |
| `decision` | `ADR-` and four digits | `docs/decisions/*.md` |

A missing key, or another `status`, shall be reported as a `parse-error`. The stopgap shall ignore keys it doesn't use, and the files `index.md` and `log.md`, which OKF reserves.

- WHEN a decision has `status: proposed` THEN the stopgap reports a `parse-error` for it.
- WHEN a spec has an extra `owner:` key THEN the stopgap reports nothing about it.

### SPECKIT-5 Items and item lines

A heading that starts with an ID shall be an item: a release (`### REL-0.1 Checker`) in the brief, a component (`### COMP-SPECKIT …`) in the architecture page, or a requirement (`### SYNC-2 …`, prefixed with its spec's ID) in a spec. Inside code blocks, and in other documents, such headings are text. The first paragraph after an item heading holds its item lines when every line starts with a name the item declares: `Capabilities:` and `Appetite:` for a release; `Paths:`, `Technology:` and `Decided by:` for a component; `Release:`, `Check:` (`auto` or `manual`) and `Verified:` for a requirement. Several pairs may share a line, separated by ` · `, and a value may be in a code span. An ID in prose is never a link.

- WHEN `### SYNC-2 …` is followed by `Release: REL-0.2 · Check: manual` THEN SYNC-2's release is REL-0.2 and its check is manual.
- WHEN a paragraph says "see SYNC-99" and SYNC-99 doesn't exist THEN nothing is reported.

### SPECKIT-6 Requirements and examples

A requirement shall have a statement and at least one example: a fenced block whose info string starts with `console`, or a line that starts with `WHEN`, optionally after a list marker, and contains `THEN`. A console example follows Rust's trycmd syntax: `$ ` starts a command, `? <code>` on the next line gives its exit code (0 by default), `...` on its own line matches any lines, and `[..]` matches any text within a line. A removed requirement's ID shall go to its spec's `retired` front-matter list.

- WHEN a requirement has neither kind of example THEN the stopgap reports a `requirement-has-example` error for it.

### SPECKIT-7 Scope

The brief's `release` field shall name the current release. A requirement's release shall be its `Release:` line or, by default, the first release whose `Capabilities:` line names its spec. A requirement shall be in scope when its release is the current one or comes before it in the brief; a requirement with no release is backlog.

- WHEN the brief's `release` is REL-0.0 THEN no requirement of REL-0.1 is in scope.

### SPECKIT-8 Spec Kit changes

Each folder under `specs/` whose name starts with a number or a `YYYYMMDD-HHMMSS` timestamp, then a hyphen, shall be a change named after the folder. Its `spec.md` ends with a `## Spec changes` section that lists requirement IDs under `Implements:` (built unchanged), `Adds:`, `Changes:` or `Removes:`, or gives a reason after `No behavior change:`. A change shall be finished when its `tasks.md` exists and every task in it is checked. Spec Kit's own `FR-` and `SC-` IDs are text.

- WHEN `specs/007-photo-upload/tasks.md` has 6 checked and 5 unchecked tasks THEN the change `007-photo-upload` is unfinished.

### SPECKIT-9 Rules

The stopgap shall apply these rules:

| Rule | Checks | Severity |
| --- | --- | --- |
| `unique-ids` | No ID appears twice, no retired ID appears again, and no two unfinished changes add the same ID | error |
| `no-dangling-links` | `Release:`, `Decided by:` and `components` values, change links, and IDs in test names point at existing items | error |
| `requirement-has-example` | Every requirement has an example | error |
| `requirement-covered` | Every in-scope requirement has a test | warning |
| `requirement-passing` | Every in-scope requirement's tests pass | warning |
| `change-lists-spec-changes` | Every change has a `## Spec changes` section | error |
| `change-reflected` | A finished change's `Implements:`, `Adds:` and `Changes:` IDs exist or are retired, and its `Removes:` IDs are retired | error |

`no-dangling-links` shall not check a release's `Capabilities:` line, the `Adds:` targets of an unfinished change, any `Removes:` target, or any link of a finished change. A `parse-error` is an error.

- WHEN an unfinished change says `Adds: SYNC-9` before SYNC-9 is written THEN no `no-dangling-links` error is reported.
- WHEN every task of `specs/007-photo-upload` is checked and its `Adds: SYNC-9` names no requirement THEN the stopgap reports a `change-reflected` error for SYNC-9.

### SPECKIT-10 Evidence

The stopgap shall read the JUnit XML report `build/test-results/junit.xml` and the test files `tests/**/*.py`, and never production code. It shall find a requirement ID in a reported test case's class and name, and on test-file lines with `def test` or `class Test`: an existing capability prefix with no capital letter or digit before it, then `-` or `_`, then the number, with no digit after it. Each requirement shall be:

- `untested`: no tests;
- `linked`: tests, but no reported pass or failure;
- `passing`: a reported pass and no failure;
- `failing`: a reported failure or error;
- `manual`: marked `Check: manual`, with a `Verified:` line and no failing test.

- WHEN `test_SYNC_2_uploads_once` passed in the report THEN SYNC-2 is `passing`.
- WHEN a test is named `test_ASYNC_2_retry` THEN no test is linked to SYNC-2.

### SPECKIT-11 Report

`check` shall print one line per finding, `<file>:<line>: <severity> <rule>: <message>`, sorted by file, line and rule, then a summary line; with `--json`, it shall print one JSON object with `schema_version`, `summary`, `findings` and `requirements` instead. It shall exit with 0 when there is no error, 1 when there is one, 2 on a usage error and 3 on an internal error. With `--staged`, it shall check the files as they are in the git index and skip `requirement-covered` and `requirement-passing`. Two runs on the same files shall print the same bytes.

```console fixture=speckit-violations
$ bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check
? 1
...
[..]: error no-dangling-links: [..]
...
errors: [..] · warnings: [..]
```

### SPECKIT-12 Stages

`status` shall show the current release and each stage, as done or with what is open. Until `bondstone approve` exists, a document is approved when its `status` is `stable`.

| Stage | Done when |
| --- | --- |
| `frame` | The brief has no errors and is approved |
| `shape` | The architecture page has no errors and is approved; every capability named by the current or an earlier release has an approved spec; every decision named in a component's `Decided by:` is approved |
| `build` | Every in-scope requirement is `passing` or `manual` |
| `release` | `build` is done, and `CHANGELOG.md` has a heading whose version starts with the release's, such as `## [0.0.0] - 2026-11-02` for REL-0.0 |

- WHEN the brief has `status: stable` and no errors THEN `frame` is done.
- WHEN `build` is done and `CHANGELOG.md` has only `## [Unreleased]` THEN `release` is open.

### SPECKIT-13 Next step

`next` shall return exactly one action with a reason, the first that applies:

1. `fix`, when there are errors;
2. `run`, with Spec Kit's command for the first missing step of the first unfinished change in folder order: `speckit.plan` without `plan.md`, `speckit.tasks` without `tasks.md`, `speckit.implement` while tasks are unchecked;
3. `write` or `approve`, for the first open stage's missing document, approval or changelog section, in this order: the brief, the architecture page, specs in the order the brief names them, decisions by ID;
4. `build`, for the in-scope capability with the most open requirements (`untested`, `linked` or `failing`, not marked `Check: manual`), ties going to the one the brief names first: as a Spec Kit change that lists them under `Implements:` when there are three or more, otherwise its first open requirement alone, with tests named after it;
5. `verify`, for a manual requirement without a `Verified:` line, asking the person to check it by hand;
6. `done`.

With `--json`, it shall print the action as one object.

- WHEN the brief, the architecture page and every decision are approved and the SPECKIT spec is a draft THEN `next` returns `approve SPECKIT`.
- WHEN SYNC has four open requirements and AUTH has one THEN `next` returns `build` with `speckit.specify` for SYNC's four.

### SPECKIT-14 Pre-commit hook

A pre-commit hook script shipped with the extension shall run `check --staged` and refuse the commit on errors. When `CLAUDE_CODE_CHILD_SESSION` is set, as Claude Code does in the shells it runs, it shall also refuse staged changes to `status` or `verified` in front-matter, or to `Verified:` lines, and say that approvals are for people.

- WHEN a shell where `CLAUDE_CODE_CHILD_SESSION` is set commits a change from `status: draft` to `status: stable` THEN the commit is refused.
- WHEN the person commits the same change from their own terminal THEN the commit goes through.

### SPECKIT-15 Preset

The preset shall append to Spec Kit's spec template a `## Spec changes` section with `Implements:`, `Adds:`, `Changes:` and `Removes:` lines and a comment that behavior lives in `docs/spec/`. It shall append to the tasks template a note that every test proving a requirement carries the requirement's ID in its name, and extend the `speckit.tasks` command so that those tests are always among the tasks, although Spec Kit treats tests as optional. It shall use the `append` strategy only.

- WHEN `/speckit-specify` creates `specs/008-export/spec.md` THEN the file ends with the `## Spec changes` section.
- WHEN `/speckit-tasks` creates `tasks.md` for a change that implements SYNC-2 THEN the tasks include a test named after SYNC-2.

### SPECKIT-16 Agent behavior
Check: manual

`/speckit-bondstone-next` shall do the action the next step names, after reading the documents it names, or tell the person what to approve or verify. Every extension command, run a second time on an unchanged repository, shall change no files.

- WHEN a fresh session runs `/speckit-bondstone-next` and the action is `approve SPECKIT` THEN the agent asks the person to approve SPECKIT and changes nothing.
