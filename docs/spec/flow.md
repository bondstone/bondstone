---
type: spec
id: FLOW
title: Status, next step and context
description: How any session learns where the project is, what to do next and what it needs to know.
status: draft
components: [COMP-STAGES, COMP-CLI]
fixture: simple-app
---

# Status, next step and context

Status, the next step and context are computed every time from the graph, the evidence and the approvals. Nothing about a session is stored, so every session gets the same answer. All three read only what the active packs declare.

## Requirements

### FLOW-1 Status

`bondstone status` shall show:

- the current release, and each stage as done or with what is open;
- each in-scope work unit (a capability spec in simple-app), with its requirement counts by evidence status and its approval state;
- each unfinished change, with its task count.

With `--json`, it shall print the same as one object.

```console
$ bondstone status
Release REL-0.1 Checker
  frame    done
  shape    done
  build    open: [..]
  release  open: [..]
...
```

### FLOW-2 One next action

`bondstone next` shall return exactly one action, of kind `fix`, `write`, `approve`, `verify`, `run`, `build` or `done`, with a reason, the blocking rules, and the context command that loads what the action needs. With `--json`, it shall print the action as one object.

```console
$ bondstone next --json
{"schema_version":1,"action":{"kind":"[..]"[..]},"reason":"[..]","blocking":[..],"context":"bondstone context [..]"}
```

### FLOW-3 Order of actions

`bondstone next` shall choose, in this order:

1. `fix`, when there are error violations;
2. `run`, for the first unfinished change in ID order, such as a Spec Kit feature: the host's command for its first missing step;
3. `write` or `approve`, for the first open stage's missing document, missing or stale approval, or missing changelog section;
4. `build`, for open requirements not marked `Check: manual`;
5. `verify`, for a manual requirement without a current verification, asking the person to check its behavior by hand;
6. `done`, when every stage of the current release is done.

- WHEN `bondstone check` reports an error and the brief isn't approved THEN `next` returns `fix`.
- WHEN `specs/007-photo-upload/tasks.md` has unchecked tasks THEN `next` returns `run speckit.implement` for that change before any other build work.
- WHEN SYNC-7 is marked `Check: manual` and SYNC-2 is untested THEN `next` returns `build` for SYNC-2 before `verify` for SYNC-7.
- WHEN every in-scope requirement is `passing` or `manual` and the changelog has no section for the release THEN `next` returns `write` for that section.

### FLOW-4 Build suggestion

For `build`, `next` shall pick the in-scope work unit with the most open requirements (`untested`, `linked` or `failing`, and not marked `Check: manual`), breaking ties by the order in which the brief names them. When a host pack is active and that work unit has three or more open requirements, `next` shall suggest starting a change with the host's command, listing them under `Implements:`; otherwise it shall suggest building its first open requirement directly. Either way it shall include the test-naming hint.

- WHEN SYNC has four open requirements and AUTH has one THEN `next` suggests `speckit.specify` for SYNC's four open requirements, listed under `Implements:`.
- WHEN SYNC's only open requirements are SYNC-3 and SYNC-5 THEN `next` suggests building SYNC-3 with tests named `test_SYNC_3_<behavior>`.
- WHEN `rules.yml` sets `host: none` and SYNC has four open requirements THEN `next` suggests building SYNC's first open requirement directly.

### FLOW-5 Context

`bondstone context <ID>` shall print Markdown with:

- the item and its nested items;
- the items reached through relations the packs mark as context, up to two hops;
- its linked tests and their status;
- the test-naming hint.

It shall print nothing else and change no file.

```console
$ bondstone context SYNC-2
# SYNC-2 [..]
...
## Tests
...
```

### FLOW-6 Brief context

`bondstone context --brief` shall print at most 40 lines: the release and its stages, the unfinished changes, the open problems and the next action. When there are more open problems than fit, it shall print the first ones and how many more there are. It is what the SessionStart hook shows.

- WHEN `bondstone check` reports 60 violations THEN `bondstone context --brief` prints at most 40 lines, says how many problems it left out, and ends with the next action.
