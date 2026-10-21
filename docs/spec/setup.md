---
type: spec
id: SETUP
title: Setup and hooks
description: How a project starts using Bondstone, wires it into commits, agent sessions and CI, and checks which version it runs.
status: draft
components: [COMP-HOOKS, COMP-WRITE, COMP-CLI]
fixture: fresh
---

# Setup and hooks

`bondstone init` adds Bondstone to a repository, and `bondstone hooks install` wires the same check into commits, Claude Code sessions and CI. Bondstone's own hooks stay minimal. Projects that want more enforcement can run Bondstone as a spec-gates custom gate. Integrations use `bondstone version` to check that the installed CLI is new enough.

## Requirements

### SETUP-1 Initialize

`bondstone init` shall create `.bondstone/rules.yml` with `bondstone: 1` and the simple-app profile, and add a short Bondstone block to `AGENTS.md`. When a `.specify/` folder exists, it shall set `host: speckit` and list every existing `specs/*` folder under `ignore:`, so that changes made before Bondstone aren't checked. In a repository that already has `.bondstone/rules.yml`, it shall change nothing and exit with 2 unless `--force` is given.

```console
$ bondstone init
Created .bondstone/rules.yml (profile simple-app, host none)
Updated AGENTS.md
$ bondstone init
? 2
[..]already initialized[..]--force[..]
```

- WHEN `bondstone init` runs in a Spec Kit project with `specs/001-auth` and `specs/002-sync` THEN `rules.yml` has `host: speckit` and both folders under `ignore`.

### SETUP-2 Pre-commit hook

`bondstone hooks install` shall install a pre-commit hook that runs `bondstone hooks run pre-commit`, in the hooks folder git uses (`git rev-parse --git-path hooks`, which follows `core.hooksPath` and worktrees). If a pre-commit hook already exists there, it shall leave the hook unchanged and print the line to add to it. `bondstone hooks run pre-commit` shall run `bondstone check --staged`, and when `CLAUDE_CODE_CHILD_SESSION` is set, it shall also refuse staged changes to `status` or `verified` in front-matter, or to `Verified:` lines, and say that approvals are for people.

- WHEN the repository already has a pre-commit hook THEN `bondstone hooks install` leaves it unchanged and prints `bondstone hooks run pre-commit || exit 1`.
- WHEN `core.hooksPath` is `.husky` THEN `bondstone hooks install` looks for the hook in `.husky/`, not in `.git/hooks/`.
- WHEN `CLAUDE_CODE_CHILD_SESSION` is set and a staged change turns `status: draft` into `status: stable` THEN the commit is refused.

### SETUP-3 Claude Code hooks
Release: REL-0.2

`bondstone hooks install` shall print the Claude Code hook configuration, without editing Claude Code's settings itself: SessionStart runs `bondstone context --brief`, Stop runs `bondstone hooks run stop`, and PreToolUse runs `bondstone hooks run pre-tool-use`. Both `hooks run` events read the hook's JSON input on stdin.

`bondstone hooks run stop` shall exit with 2 and print the violations on stderr when the files that differ from `HEAD`, untracked files included, or their direct neighbours in the graph have error violations, so that the agent keeps working. It shall exit with 0 when there are none, when the input's `stop_hook_active` is true, and on a configuration or internal error.

`bondstone hooks run pre-tool-use` shall exit with 2 and give the reason when a Bash call runs `bondstone approve` or `bondstone verify`, or when an Edit, Write or NotebookEdit call would change `status` or `verified` in an existing document's front-matter, or a `Verified:` line.

- WHEN `bondstone hooks run pre-tool-use` receives a Bash call running `bondstone approve SYNC --yes` THEN it exits with 2 and says that approvals are for people.
- WHEN `bondstone hooks run stop` receives `stop_hook_active: false` and an uncommitted spec has a dangling link THEN it exits with 2 and prints that violation on stderr.
- WHEN `bondstone hooks run stop` receives `stop_hook_active: true` THEN it exits with 0, even if errors remain.

### SETUP-4 CI workflow

Bondstone shall ship an example GitHub Actions workflow that runs the project's tests with a JUnit report and then `bondstone check --all` on every pull request.

- WHEN the example workflow runs on a pull request that breaks an error rule THEN the job fails.

### SETUP-5 spec-gates recipe

`bondstone hooks install --gates` shall print the spec-gates policy entry that runs `bondstone check --all` as a custom gate at every boundary, and shall not write any spec-gates file.

```console
$ bondstone hooks install --gates
...
"bondstone": {"orchestrator": "custom", "custom_command": "bondstone check --all", "severity": "error"}
...
```

### SETUP-6 Version

`bondstone version` shall print the CLI's version. With `--json`, it shall print one object with the `schema_version` of Bondstone's JSON output and the `version`, so that integrations can check they are compatible.

```console
$ bondstone version --json
{"schema_version":1,"version":"[..]"}
```
