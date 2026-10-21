---
type: spec
id: PROFILE
title: simple-app profile
description: The documents, IDs, rules and stages of the simple-app profile.
status: draft
components: [COMP-CONFIG, COMP-RULES, COMP-STAGES]
fixture: simple-app
---

# simple-app profile

simple-app is Bondstone's first profile, for small apps and tools such as Bondstone itself. People approve what the app does, tests prove it, and Bondstone computes the rest. The profile ships as two packs: `simple-app` (documents, rules and stages) and the host pack `speckit` (Spec Kit changes). In the core's terms, a capability spec is the owner, the work unit and the scope carrier of its requirements.

## Requirements

### PROFILE-1 Documents

The simple-app pack shall declare these document types and default paths. A project may change any path under `paths:` in `rules.yml`, and Bondstone shall not read files or folders that match a glob under `ignore:`.

| Type | ID | Default path | Holds |
| --- | --- | --- | --- |
| `brief` | `BRIEF` | `docs/brief.md` | Problem, users, goals, principles and releases (`REL-…` items) |
| `architecture` | `ARCH` | `docs/architecture.md` | Context, quality goals, components (`COMP-…` items), flows, decisions and risks |
| `spec` | the capability's prefix, for example `SYNC` | `docs/spec/*.md` | One capability's requirements (`SYNC-1`, `SYNC-2`, …) |
| `decision` | `ADR-0001`, `ADR-0002`, … | `docs/decisions/*.md` | One decision in MADR's form |
| changelog | none | `CHANGELOG.md` | One section per release |

- WHEN `rules.yml` sets `paths: {brief: BRIEF.md}` THEN Bondstone reads the brief from `BRIEF.md` and ignores `docs/brief.md`.
- WHEN `rules.yml` sets `ignore: [specs/004-sync]` THEN `bondstone check` reports nothing about that folder.

### PROFILE-2 IDs

A capability prefix shall be 3 to 12 uppercase letters, unique, and not one of the reserved prefixes `BRIEF`, `ARCH`, `ADR`, `COMP` and `REL`. A requirement ID shall be the prefix of the spec it is written in, a hyphen and a positive number. A component ID shall be `COMP-` followed by uppercase letters and digits, and a release ID `REL-` followed by a version. The `valid-ids` rule shall report every other ID of these types as an error.

- WHEN a capability spec declares `id: UI` THEN `bondstone check` reports a `valid-ids` error saying a prefix needs at least 3 letters.
- WHEN `docs/spec/sync.md` contains the heading `### AUTH-1 Sign in` THEN `bondstone check` reports a `valid-ids` error for AUTH-1.

### PROFILE-3 Retired IDs

When a requirement is removed, its ID shall be added to the `retired` list in its spec's front-matter, and `unique-ids` shall report an error when a retired ID appears again as an item.

- WHEN SYNC-4 is listed under `retired` and a heading `### SYNC-4 Batch uploads` is added THEN `bondstone check` reports a `unique-ids` error for SYNC-4.

### PROFILE-4 Requirement shape

A requirement shall be a heading `### <ID> <title>`, followed by optional item lines `Release:` and `Check: auto` or `Check: manual`, a statement of the behavior, and at least one example. The `requirement-has-example` rule shall report an error for a requirement without an example.

```console fixture=violations
$ bondstone check
? 1
...
[..]: error requirement-has-example: [..]
...
```

### PROFILE-5 Examples

An example shall be either a fenced code block whose info string starts with `console`, or a line that starts with `WHEN`, optionally after a list marker, and contains `THEN`. In a console example, which follows the syntax of Rust's trycmd:

- `$ ` starts a command;
- `? <code>` on the line after a command gives its expected exit code, 0 by default;
- `...` on its own line matches any number of lines;
- `[..]` matches any text within a line.

A command's expected output is compared with its stdout followed by its stderr. Bondstone shall not run examples. A project's test runner may run console examples and should name each result after its requirement.

- WHEN a requirement contains `- WHEN the device is offline THEN the entry is saved locally` THEN `requirement-has-example` passes for it.

### PROFILE-6 Releases and scope

The brief's front-matter `release` shall name the current release. A requirement's release shall be its `Release:` item line or, by default, the first release whose `Capabilities:` line names its spec. A requirement shall be in scope when its release is the current release or appears before it in the brief. A requirement with no release is backlog: never in scope, but checked by every structural rule. A release's `Capabilities:` line may name capabilities whose specs don't exist yet.

- WHEN the brief lists REL-0.1 before REL-0.2 and its `release` is REL-0.1 THEN `requirement-covered` doesn't warn for untested requirements of REL-0.2.
- WHEN no release names the EXPORT spec and EXPORT-1 has no `Release:` line THEN EXPORT-1 is backlog and `requirement-covered` doesn't warn for it.

### PROFILE-7 Components and code ownership

A component shall have `Paths:` and `Technology:` item lines and a contract paragraph, or the `component-complete` rule reports an error. Every file tracked or staged in git that matches the `code` globs in `rules.yml` shall match some component's `Paths`, or the `code-has-owner` rule reports a warning.

- WHEN `src/bondstone/cache.py` is committed and no component's `Paths` match it THEN `bondstone check` warns `code-has-owner` for that file.

### PROFILE-8 Spec Kit changes

A Spec Kit change's `spec.md` shall contain a `## Spec changes` section listing requirement IDs on at least one of `Implements:`, `Adds:`, `Changes:` or `Removes:`, or a line `No behavior change:` followed by a reason; otherwise `change-lists-spec-changes` reports an error. `Implements:` names requirements the change builds without changing them.

A change shall be finished when its `tasks.md` exists and every task in it is checked. When a change is finished, every `Implements:`, `Adds:` and `Changes:` ID shall exist or be retired, and every `Removes:` ID shall be retired; otherwise `change-reflected` reports an error. Two unfinished changes that add the same ID shall raise a `unique-ids` error. The speckit pack shall name each change's steps: `plan.md` comes from `speckit.plan`, `tasks.md` from `speckit.tasks`, and checked tasks from `speckit.implement`.

- WHEN every task of `specs/007-photo-upload` is checked and its `Adds: SYNC-9` names no existing requirement THEN `bondstone check` reports a `change-reflected` error for SYNC-9.

### PROFILE-9 Link exemptions

`no-dangling-links` shall not check the `Adds:` targets of an unfinished change, any `Removes:` target, any link of a finished change, or a release's `Capabilities:` line. The `Implements:` and `Changes:` targets of an unfinished change are checked.

- WHEN an unfinished change says `Adds: SYNC-9` before SYNC-9 is written THEN no `no-dangling-links` error is reported.
- WHEN an unfinished change says `Implements: SYNC-30` and SYNC-30 doesn't exist THEN `bondstone check` reports a `no-dangling-links` error.

### PROFILE-10 Rule set

The simple-app and speckit packs shall contain exactly these rules, with these default severities:

| Rule | Pack | Severity |
| --- | --- | --- |
| `unique-ids` | simple-app | error |
| `valid-ids` | simple-app | error |
| `no-dangling-links` | simple-app | error |
| `requirement-has-example` | simple-app | error |
| `requirement-covered` | simple-app | warning |
| `requirement-passing` | simple-app | warning |
| `component-complete` | simple-app | error |
| `code-has-owner` | simple-app | warning |
| `change-lists-spec-changes` | speckit | error |
| `change-reflected` | speckit | error |

The parse findings `parse-error`, `misplaced-item`, `bad-link-value` and `unknown-item-line` come from the scanner (GRAPH), not from a pack. The release gate (CHECK-11) reports gaps in evidence as errors.

- WHEN the `every-rule` fixture, which breaks each rule once, is checked with no overrides THEN `bondstone check --json` reports exactly ten violations, one for each rule.

### PROFILE-11 Stages
Release: REL-0.2

The simple-app pack shall define four stages, computed on every run. An approval counts only while it is current (APPROVE-4); a `status` of `stable` or `accepted` alone doesn't count.

| Stage | Done when |
| --- | --- |
| `frame` | The brief exists, has no error violations, and its approval is current |
| `shape` | The architecture has no error violations and its approval is current; every capability named by the current or an earlier release has a spec whose approval is current; every decision named in a component's `Decided by:` is approved and current |
| `build` | Every in-scope requirement is `passing` or `manual` |
| `release` | `build` is done, every approval the stages need is current, and the changelog has a heading with the release's version (the part of its ID after `REL-`), alone or followed by further version parts: `## [0.1.0] - 2026-11-20` counts for REL-0.1, `## [0.10.0]` doesn't |

- WHEN the brief is approved and unchanged since THEN `frame` is done.
- WHEN a capability named by the current release has no spec THEN `shape` is open and `bondstone next` asks to write it.
- WHEN every in-scope requirement is `passing` or `manual` THEN `build` is done.
- WHEN `build` is done but `CHANGELOG.md` has only an `## [Unreleased]` heading THEN `release` is open for REL-0.1.

### PROFILE-12 Front-matter

Every simple-app document except the changelog shall have front-matter with `type`, `id`, `title`, `description` and `status`. `status` shall be `draft` or `stable` for briefs, architecture pages and specs, and `proposed`, `accepted`, `rejected`, `deprecated` or `superseded` for decisions. A missing key or another `status` shall be reported as a `parse-error`. Keys that no pack declares shall be accepted without a finding.

- WHEN a decision's front-matter has no `title` THEN `bondstone check` reports a `parse-error` for that file.
- WHEN a capability spec has `status: done` THEN `bondstone check` reports a `parse-error` for that file.
- WHEN a capability spec has an extra `owner:` key THEN `bondstone check` reports nothing about it.

### PROFILE-13 Item types

The simple-app pack shall declare these inline item types. Each is declared by a `###` heading that starts with its ID, never by a list item, and has only these item lines:

| Type | Declared in | Item lines |
| --- | --- | --- |
| Release `REL-…` | the brief | `Capabilities:` capability specs · `Appetite:` text |
| Component `COMP-…` | the architecture | `Paths:` globs · `Technology:` text · `Decided by:` decisions |
| Requirement `<prefix>-<n>` | its capability spec | `Release:` a release · `Check:` `auto` or `manual` · `Verified:` written by `bondstone verify` |

The front-matter relations are `release` (a release) on the brief and `components` (components) on capability specs; a capability spec's `retired` field lists its retired IDs. The speckit pack declares the change type, whose links are in its `## Spec changes` section: `Implements:`, `Adds:`, `Changes:` and `Removes:` (requirements) and `No behavior change:` (text).

- WHEN a release heading is followed by `Capabilities: SYNC, AUTH · Appetite: 2 weeks` THEN the release links to SYNC and AUTH, and no `bad-link-value` error is reported.
