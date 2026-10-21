---
type: spec
id: SPECKIT
title: Spec Kit integration
description: The Spec Kit extension and preset that let agents drive Bondstone from inside Spec Kit, and the stopgap behind them until the CLI takes over.
status: draft
components: [COMP-SPECKIT]
fixture: speckit-project
---

# Spec Kit integration

The `bondstone` extension gives agents four commands, and the `bondstone` preset adds two things to Spec Kit: the `## Spec changes` section that ties a change to the living spec, and test naming. Spec Kit's own commands stay unchanged. Until the CLI takes over, a stopgap script behind the four commands applies the profile's rules and computes the stage and the next step, so the agent never computes either.

## Requirements

### SPECKIT-1 Four commands

When installed with `specify extension add`, the `bondstone` extension shall register exactly four commands: `speckit.bondstone.status`, `speckit.bondstone.next`, `speckit.bondstone.write` and `speckit.bondstone.check`. Claude Code installs them as skills, typed `/speckit-bondstone-status` and so on.

- WHEN the extension is installed into a Spec Kit 1.2 project THEN `specify extension list` shows `bondstone` with four commands.

### SPECKIT-2 Command files

The command files shall name no document type, rule or pack, and shall relay what the wrapper script prints instead of computing a status, a stage or a next step themselves. Each shall tell the agent never to edit `rules.yml`, never to change `status`, `verified` or a `Verified:` line, never to run `bondstone approve` or `bondstone verify`, and never to reuse an ID.

- WHEN the lint test scans the extension's command files THEN it finds no type, rule or pack names from the shipped packs, and finds every prohibition in each file.

### SPECKIT-3 Wrapper script

The extension's wrapper script shall run the backend that serves each command, pass its arguments through, and exit with the backend's exit code. The backend is the stopgap until the CLI serves the command (SPECKIT-10, SPECKIT-11).

```console
$ bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check
errors: 0 · warnings: 0 · signals: 0
```

### SPECKIT-4 Stopgap check

The stopgap shall apply `unique-ids`, `no-dangling-links`, `requirement-has-example`, `requirement-covered`, `requirement-passing`, `change-lists-spec-changes` and `change-reflected` as the PROFILE spec defines them, read evidence as EVIDENCE-2 to EVIDENCE-5 define it for the `pytest` style, and report in the formats of CHECK-2 and CHECK-3 with the exit codes of CHECK-1. With `--staged`, it shall check the files as they are in the git index and skip the two evidence rules, as CHECK-5 does.

```console fixture=speckit-violations
$ bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check
? 1
...
[..]: error no-dangling-links: [..]
  fix: [..]
...
```

### SPECKIT-5 Stopgap status and next step

The stopgap shall compute each requirement's evidence status, the stages of PROFILE-11 and one next action as FLOW-2 to FLOW-4 define them, and print them in the formats of FLOW-1 and FLOW-2. Until `bondstone approve` exists, it shall count a `status` of `stable` or `accepted` as a current approval, and any `Verified:` line under a `Check: manual` requirement as a current verification.

- WHEN the brief has `status: stable` and no `verified` field THEN the stopgap reports `frame` as done.
- WHEN the brief, the architecture page and every decision are approved and the SPECKIT spec is a draft THEN `next` returns `approve SPECKIT`.

### SPECKIT-6 Pre-commit hook

A pre-commit hook script shipped with the extension shall run the stopgap's check on the staged files and refuse the commit on errors. When `CLAUDE_CODE_CHILD_SESSION` is set, it shall also refuse staged changes to `status` or `verified` in front-matter, or to `Verified:` lines, and say that approvals are for people.

- WHEN a shell where `CLAUDE_CODE_CHILD_SESSION` is set commits a change from `status: draft` to `status: stable` THEN the commit is refused.
- WHEN the person commits the same change from their own terminal THEN the commit goes through.

### SPECKIT-7 Spec changes section

The preset shall append to Spec Kit's spec template a `## Spec changes` section with `Implements:`, `Adds:`, `Changes:` and `Removes:` lines, and a comment telling the agent that behavior lives in `docs/spec/` and to read the capability's spec first. It shall use the `append` strategy only.

- WHEN `/speckit-specify` creates `specs/008-export/spec.md` in a project with the preset THEN the file ends with the `## Spec changes` section.

### SPECKIT-8 Test naming

The preset shall append to Spec Kit's tasks template a note that every test proving a requirement carries the requirement's ID in its name, and extend the `speckit.tasks` command so that those tests are always among the tasks, although Spec Kit treats tests as optional.

- WHEN `/speckit-tasks` creates `tasks.md` for a change that implements SYNC-2 THEN the tasks include a test named after SYNC-2, and the file ends with the test-naming note.

### SPECKIT-9 Agent behavior
Check: manual

`/speckit-bondstone-next` shall do the action the next step names, after reading the documents it names, or tell the person what to approve or verify. Every extension command, run a second time on an unchanged repository, shall change no files.

- WHEN a fresh session runs `/speckit-bondstone-next` and the action is `approve SPECKIT` THEN the agent asks the person to approve SPECKIT and changes nothing.

### SPECKIT-10 CLI-backed check
Release: REL-0.1

The wrapper script shall run `bondstone check` for `check`, and feed `bondstone check --json` to the stopgap for `status` and `next`. When `bondstone` is missing or older than the version the extension requires, it shall exit with 2 and print one install instruction.

```console fixture=speckit-without-cli
$ bash .specify/extensions/bondstone/scripts/bash/bondstone.sh check
? 2
[..]uv tool install bondstone[..]
```

### SPECKIT-11 CLI-backed status, next and write
Release: REL-0.2

The wrapper script shall run `bondstone status` and `bondstone next`, the `write` command shall create documents with `bondstone new`, get new IDs from `bondstone id next` and add links with `bondstone link`, and the extension shall ship no stopgap.

- WHEN the 0.2 extension is installed THEN its `scripts` folder has no stopgap, and `/speckit-bondstone-next` relays what `bondstone next` returns.
