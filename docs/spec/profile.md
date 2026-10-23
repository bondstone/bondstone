---
type: spec
id: PROFILE
title: simple-app profile
description: The documents, items, scope, stages, changes and rules of the simple-app profile.
status: draft
components: [COMP-SPECKIT]
fixture: simple-app
---

# simple-app profile

simple-app is Bondstone's first profile, for small apps and tools such as Bondstone itself: a brief, an architecture page, one living spec per capability, and decision records for hard choices. In release 0.0 the Spec Kit extension's stopgap applies it.

## Requirements

### PROFILE-1 Documents

The profile shall consist of these documents. Each is a Markdown file whose front-matter follows Open Knowledge Format 0.2 and has `type`, `id`, `title`, `description` and `status`; `status` is `draft`, `stable` or `deprecated`.

| Type | ID | Path |
| --- | --- | --- |
| `brief` | `BRIEF` | `docs/brief.md` |
| `architecture` | `ARCH` | `docs/architecture.md` |
| `spec` | its capability prefix, such as `SYNC` | `docs/spec/*.md` |
| `decision` | `ADR-` and four digits | `docs/decisions/*.md` |

A missing key, or another `status`, shall be reported as a `parse-error`. Keys the profile doesn't use, and the files `index.md` and `log.md`, which OKF reserves, shall be ignored.

- WHEN a decision has `status: proposed` THEN a `parse-error` is reported for it.
- WHEN a spec has an extra `owner:` key THEN nothing is reported about it.

### PROFILE-2 Items and item lines

A heading that starts with an ID shall be an item: a release (`### REL-0.1 Checker`) in the brief, a component (`### COMP-SPECKIT …`) in the architecture page, or a requirement (`### SYNC-2 …`, prefixed with its spec's ID) in a spec. Inside code blocks, and in other documents, such headings are text. The first paragraph after an item heading holds its item lines when every line starts with a name the item declares: `Capabilities:` and `Appetite:` for a release; `Paths:`, `Technology:` and `Decided by:` for a component; `Release:`, `Check:` (`auto` or `manual`) and `Verified:` for a requirement. Several pairs may share a line, separated by ` · `, and a value may be in a code span. An ID in prose is never a link.

- WHEN `### SYNC-2 …` is followed by `Release: REL-0.2 · Check: manual` THEN SYNC-2's release is REL-0.2 and its check is manual.
- WHEN a paragraph says "see SYNC-99" and SYNC-99 doesn't exist THEN nothing is reported.

### PROFILE-3 Requirements and examples

A requirement shall have a statement and at least one example: a fenced block whose info string starts with `console`, or a line that starts with `WHEN`, optionally after a list marker, and contains `THEN`. A console example follows Rust's trycmd syntax: `$ ` starts a command, `? <code>` on the next line gives its exit code (0 by default), `...` on its own line matches any lines, and `[..]` matches any text within a line. A removed requirement's ID shall go to its spec's `retired` front-matter list.

- WHEN a requirement has neither kind of example THEN a `requirement-has-example` error is reported for it.

### PROFILE-4 Scope

The brief's `REL-…` headings shall be the releases, in the brief's order, and its `release` field shall name the current one. A requirement's release shall be its `Release:` line or, by default, the first release whose `Capabilities:` line names its spec. A requirement shall be in scope when its release is the current one or comes before it; a requirement with no release is backlog.

- WHEN the brief's `release` is REL-0.0 THEN no requirement of REL-0.1 is in scope.

### PROFILE-5 Rules

The profile shall have these rules:

| Rule | Checks | Severity |
| --- | --- | --- |
| `unique-ids` | No ID appears twice, and no retired ID appears again | error |
| `no-dangling-links` | `Release:`, `Decided by:` and `components` values, and IDs in test names, point at existing items | error |
| `requirement-has-example` | Every requirement has an example | error |
| `requirement-covered` | Every in-scope requirement has a test | warning |
| `requirement-passing` | Every in-scope requirement's tests pass | warning |

`no-dangling-links` shall not check a release's `Capabilities:` line, which may name capabilities whose specs aren't written yet. A `parse-error` is an error.

- WHEN REL-0.1 names GRAPH and `docs/spec/graph.md` doesn't exist THEN no `no-dangling-links` error is reported.

### PROFILE-6 Stages

The profile shall have four stages, each done or open, computed on every run. A document is approved when its `status` is `stable`.

| Stage | Done when |
| --- | --- |
| `frame` | The brief has no errors and is approved |
| `shape` | The architecture page has no errors and is approved; every capability named by the current or an earlier release has an approved spec; every decision named in a component's `Decided by:` is approved |
| `build` | Every in-scope requirement is `passing` or `manual` |
| `release` | `build` is done, and `CHANGELOG.md` has a heading whose version starts with the release's, such as `## [0.0.0] - 2026-11-02` for REL-0.0 |

- WHEN the brief has `status: stable` and no errors THEN `frame` is done.
- WHEN `build` is done and `CHANGELOG.md` has only `## [Unreleased]` THEN `release` is open.

### PROFILE-7 Changes

A change is a host's unit of work in progress; the host says where changes are, where their links are written, and when a change is finished. A change shall list the requirements it touches on `Implements:` (built unchanged), `Adds:`, `Changes:` and `Removes:` lines, or give a reason on a `No behavior change:` line. Without a host, there are no changes.

- WHEN a change says `Implements: SYNC-2, SYNC-3` THEN it links to SYNC-2 and SYNC-3 without changing them.

### PROFILE-8 Change rules

The profile shall have these rules for changes:

| Rule | Checks | Severity |
| --- | --- | --- |
| `change-lists-requirements` | Every change has at least one of the lines of PROFILE-7 | error |
| `change-reflected` | A finished change's `Implements:`, `Adds:` and `Changes:` IDs exist or are retired, and its `Removes:` IDs are retired | error |

`unique-ids` shall also report two unfinished changes that add the same ID. `no-dangling-links` shall also check change links, except the `Adds:` targets of an unfinished change, any `Removes:` target, and any link of a finished change.

- WHEN an unfinished change says `Adds: SYNC-9` before SYNC-9 is written THEN no `no-dangling-links` error is reported.
- WHEN a finished change says `Adds: SYNC-9` and no requirement SYNC-9 exists THEN a `change-reflected` error is reported for SYNC-9.
