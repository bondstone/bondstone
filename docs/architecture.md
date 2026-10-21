---
type: architecture
id: ARCH
title: Bondstone architecture
description: How the Bondstone CLI and its Spec Kit bundle are built, what each component promises, and which decisions shape them.
status: draft
---

# Bondstone architecture

## Context

Bondstone runs on a developer's machine and in CI, inside a git repository. It reads documents, test reports and test files, and prints findings, evidence statuses, the stage and one next step. It never opens a network connection, never calls a model and never reads production code.

| Input | Where it comes from | Read by |
| --- | --- | --- |
| Markdown documents with front-matter | Tracked files: the git index for `check --staged`, `git ls-files` otherwise | COMP-GRAPH |
| Host change folders (Spec Kit's `specs/`) | The same, at the paths the host pack declares | COMP-GRAPH |
| The active-change file, if the host pack names one | The working tree, such as `.specify/feature.json` | COMP-STAGES |
| JUnit XML reports | The paths named in the configuration | COMP-EVIDENCE |
| Test files | Tracked files matching the configuration's test globs | COMP-EVIDENCE |
| Profile and packs | `.bondstone/config.yml` and the built-in packs | COMP-CONFIG |

Callers are people, the Spec Kit extension's commands, the git pre-commit hook, Claude Code hooks and CI. All of them call the CLI, or the stopgap script before it (see Bootstrap); none computes findings, statuses or the stage on its own.

Bondstone needs git and runs on Linux and macOS with CPython 3.11 to 3.13. Native Windows comes later.

## Quality goals

| Goal | Measure |
| --- | --- |
| Deterministic | The same inputs give the same output, on any supported machine and in any session |
| Fast | `check --staged` finishes in under 1 s, start-up included, on a repository of 200 documents |
| Visible approvals | Agents cannot approve or verify through any supported path, and any other change to an approval shows in CI |
| Host-agnostic core | A second host needs only a host pack and its own bundle; no command changes |
| Small | A profile adds packs, never commands; the CLI keeps its 13 commands |

## Core concepts

The core knows only these concepts. Document names, ID prefixes, rules and stages come from the profile.

- **Item:** something with a stable ID, found in a document. A document is an item; so is a requirement heading inside one.
- **Type:** declared by a pack, with an ID pattern, where its items are found (front-matter, a heading pattern or a host's folder name) and which fields they carry.
- **Link:** a typed reference from one item to another, read from front-matter fields and labeled lines such as `Decided by:`. An ID in prose is never a link.
- **Owner:** every requirement has exactly one owner, the document it is written in.
- **Grouping:** a link type the profile declares to group requirements. The profile also names the *work unit*, the type `next` names work on ("build GRAPH-1 to GRAPH-6"), and the *scope carrier*, the type whose release puts requirements in scope. Stage criteria count work units, never capabilities.
- **Scope:** a requirement is in scope when its release is the current release or an earlier one. The nearest explicit release wins: the requirement's own `Release:` line, then its owner's, then its work unit's. Releases are ordered as the brief declares them.
- **Evidence:** a requirement's status: untested, linked, passing, failing or manual.
- **Approval:** a person's `status` change, plus a `verified` record from 0.2.
- **Active change:** the change in progress, found by the host pack with one of a fixed set of locators: a field in a JSON or YAML file, the current git branch matched against change IDs, or the item whose status field has a given value. If the locator finds none, or more than one, there is no active change and `next` follows the brief's order. `next` and `context` start from the active change, or from an ID they are given. The file a locator reads is an input like any other; Bondstone never asks a host's own tools. Nothing else about a session is stored. A host whose active work fits none of these locators needs a new one in the core and a new pack schema version, but no new command.

In the simple-app profile, the owner, the work unit and the scope carrier are all the living spec of one capability. The brief's `Capabilities:` line declares each capability and the release that starts it; the capability's spec, once written, carries the same ID and adds its requirements. A declared capability without a spec is not a dangling link: the shape stage asks for the spec once its release is in scope. That a requirement's prefix equals its spec's ID is a simple-app rule, not a core one.

## Bootstrap

The extension's four commands keep their names from 0.0; what runs behind them moves to the CLI over three releases.

| Behind | 0.0 | 0.1 | 0.2 |
| --- | --- | --- | --- |
| `check` | Stopgap script | `bondstone check` | `bondstone check` |
| `status`, `next` | Stopgap script | Stopgap, reading `bondstone check --json` | `bondstone status`, `bondstone next` |
| `write` | Prompt | Prompt | Prompt calling `new`, `id next` and `link` |
| Pre-commit hook | Stopgap check and the agent block | `bondstone hooks run` | `bondstone hooks run` |

The stopgap computes statuses, the stage and the next step itself and prints them in the CLI's JSON schema, so every command body relays JSON from 0.0 on and the agent never computes a step. It is deleted in 0.2.

## Stored state

Bondstone stores only what a person decides; everything else is computed on each run.

| What | Where | Written by |
| --- | --- | --- |
| Approval | `status`, and `verified` (actor, time, hash), in the document's front-matter | A person sets `status`; `approve` adds `verified` from 0.2 |
| Manual check | A `Verified:` line under a `Check: manual` requirement | A person until 0.2, then `verify` |
| Retired IDs | The `retired` list in the owning document's front-matter | A person, when a requirement is removed |

The hash covers the whole document after normalization: UTF-8 without a BOM, LF line endings, Unicode NFC, no trailing whitespace, one final newline, and front-matter without `status` and `verified`. It is stored with a version prefix, such as `sha256-n1:`, so a later change to normalization never silently makes every approval stale. Times are quoted RFC 3339 strings in UTC.

Only these commands write files, and only the files named here:

| Command | Writes |
| --- | --- |
| `init` | `.bondstone/config.yml` and starter documents |
| `new` | A new document from a pack template |
| `link` | A link line in the named document |
| `approve` | `verified` in the named document |
| `verify` | A `Verified:` line under the named requirement |
| `hooks install` | The git pre-commit hook, and Claude Code hook entries merged into `.claude/settings.json` |

`id next` prints the next free ID, one above the highest existing or retired ID, and writes nothing; `unique-ids` catches two branches that take the same one.

## Trust model

Bondstone cannot stop a determined agent. It makes an agent's approval hard to make by accident and impossible to hide.

1. **From 0.0:** the pre-commit hook rejects staged changes to `status` or `verified` when `CLAUDE_CODE_CHILD_SESSION` is set, which Claude Code sets in every shell it runs.
2. **From 0.2:** `approve` and `verify` refuse to run in that environment or without a terminal. Claude Code hooks compare each edit's front-matter before and after, and deny changes to `status` and `verified`. A snapshot taken at the start of each turn catches changes made through the shell and restores them. The hooks block when they fail.
3. **In CI:** hashes are re-checked, and any change to approvals, packs, overrides or hook settings is reported as a review signal. `git commit --no-verify` does not skip CI.

The hash detects staleness; it is not a signature. An agent with shell access can still write a valid record, and the person sees it in review. Evidence has the same limit: Bondstone proves that a test named after a requirement ran and passed, not that it tests the requirement. Console examples that run as tests close part of that gap.

## Contracts

- **JSON:** every `--json` output carries `"schema": "bondstone/<command>@1"`, versioned apart from the package. With exit code 2 or 3 it is `{"schema": …, "error": {"code": …, "message": …}}`. The schema files are committed and tested.
- **Exit codes:** 0 clean or warnings only; 1 at least one error finding, malformed documents included; 2 configuration or usage error, raised before any document is read; 3 internal error. `status`, `next` and `context` report findings but exit 0 unless they cannot run.
- **Configuration and packs:** each file starts with `bondstone: 1`, and an unknown major version exits with 2. YAML is loaded strictly: duplicate keys are rejected, and no value is read as a date, or as a boolean other than `true` or `false`.
- **Bundle and CLI:** the Spec Kit bundle declares the CLI versions and JSON schema versions it supports, and the Spec Kit versions it needs (`>=1.2.0,<2.0.0`). Each command body first checks `bondstone version --json` and stops with an install or upgrade message on a mismatch.

## Determinism

Output is a pure function of the inputs listed under Context. Items sort by natural ID order (`SYNC-2` before `SYNC-10`), then by path, then by line, never by locale or hash order. Paths are POSIX and relative to the repository root. Output carries no wall-clock time, absolute paths, durations or environment details. Text is normalized as for hashing before it is scanned. There is no persistent cache. Only `approve` and `verify` record a time, on purpose.

## Components

Data flows one way: configuration, then the graph, then evidence, then rules, then stages; the command layer formats the result. Writers and hooks sit beside that flow and call into it, and only writers change documents.

### COMP-CLI Command layer

Paths: `src/bondstone/__init__.py`, `src/bondstone/__main__.py`, `src/bondstone/cli/`, `pyproject.toml`, `uv.lock`\
Technology: Python 3.11+, Typer, uv\
Decided by: ADR-0001

Parses arguments, runs the pipeline and prints text or JSON. It owns the 13 commands (`check`, `status`, `next`, `context`, `new`, `id next`, `link`, `approve`, `verify`, `init`, `hooks install`, `hooks run` and `version`), the exit codes and the JSON schemas. Commands import only what they use, and the hook path never loads Rich, so start-up stays under 100 ms; a CI timing test guards it.

### COMP-CONFIG Configuration and packs

Paths: `src/bondstone/config/`, `src/bondstone/packs/`\
Technology: Python, PyYAML with its C loader\
Decided by: ADR-0004

Loads the profile named in `.bondstone/config.yml`, resolves its packs and validates them against a schema. Returns one merged, immutable configuration: types, links, rules with their severities, stages, templates, report paths, test and code globs, and overrides. Each rule declares a severity and may declare a stricter one for `--release`; the `signal` severity never fails a run. An override names a rule, an item and a reason, and lives only in the configuration. A pack may add types, rules, stages or templates; it may never add a command. An invalid configuration exits with code 2 before any document is read.

### COMP-GRAPH Document graph

Paths: `src/bondstone/graph/`\
Technology: Python, a front-matter and heading scanner, `git ls-files` and `git cat-file --batch`\
Decided by: ADR-0004

Reads tracked files, from the git index for `--staged`, and finds items and links using only front-matter, headings and labeled lines; it never parses prose. Host change folders are read at the paths and with the types the host pack declares. Returns every item with its type, ID, owner, file, line, fields and document hash, and every link with its source and target. Given the same files, it returns the same graph in the same order.

### COMP-RULES Rule engine

Paths: `src/bondstone/rules/`\
Technology: Python\
Decided by: ADR-0004

Runs the rules the profile enables over the graph and evidence, then applies overrides. Each finding carries a rule ID, severity, item ID, file and line. `--release` selects each rule's release severity. `--staged` still builds the whole graph, but runs only structural rules and reports findings on items in staged files and on links into or out of them; evidence rules run with `--all` and in CI, after the tests.

### COMP-EVIDENCE Test evidence

Paths: `src/bondstone/evidence/`\
Technology: Python, `xml.etree` on JUnit XML\
Decided by: ADR-0002

Reads the JUnit reports named in the configuration, in sorted path order, and finds requirement IDs in each test's class and name. The pattern is built from the prefixes the graph declares: a prefix not preceded by a capital letter or digit, then `-` or `_`, then a number not followed by a digit. So `TestSYNC_2_uploads` proves `SYNC-2`, and `SYNC_21` does not. A test may name several IDs. A requirement is failing if any of its tests failed or errored, passing if at least one passed and none failed, and linked if its tests were only skipped or have no result. Tests exist when an ID appears in a tracked file matching the test globs. A test that names an unknown ID is reported as a dangling link.

### COMP-STAGES Stages and flow

Paths: `src/bondstone/stages/`\
Technology: Python\
Decided by: ADR-0003

Computes the project's stage, each requirement's status and one next step from the graph, evidence, findings and approvals, and answers `status`, `next` and `context <ID>`. Nothing it computes is stored. An approval is current while its hash matches the document, and stale after any edit. The next step names one action on one work unit or item: errors first, then the earliest unmet stage criterion, starting from the active change and breaking ties by the brief's order, then by ID.

### COMP-WRITE Writers

Paths: `src/bondstone/write/`\
Technology: Python, templates from packs\
Decided by: ADR-0003, ADR-0006

Implements `new`, `id next`, `link`, `approve` and `verify`. `new` creates a document from a pack template, `link` adds a link line, `approve` writes `verified` and `verify` writes a `Verified:` line; each changes only the file it is named for. `approve` and `verify` refuse to run without a terminal or when `CLAUDE_CODE_CHILD_SESSION` is set.

### COMP-SPECKIT Spec Kit integration

Paths: `speckit/`, `src/bondstone/hosts/speckit/`\
Technology: Spec Kit 1.2+ extension, preset and bundle; a host pack in YAML\
Decided by: ADR-0005

The host pack is the only place that knows Spec Kit. It declares the change folders (`specs/NNN-slug/` or `specs/YYYYMMDD-HHMMSS-slug/`), takes the change ID from the folder name, reads the `## Spec changes` section, finds the active change with the file-field locator on `.specify/feature.json`'s `feature_directory`, and ignores Spec Kit's own `FR-` and `SC-` IDs. A change is finished when every task in its `tasks.md` is ticked.

The bundle, in `speckit/extension/` and `speckit/preset/`, adds the four commands, appends `## Spec changes` to the spec template, and wraps the tasks command so that tests are named after requirement IDs. Command bodies relay JSON from the stopgap or the CLI and never compute a step; in Claude Code they are typed as `/speckit-bondstone-next` and so on. The 0.0 stopgap ships inside the extension, in `speckit/extension/scripts/`. Each `speckit-v*` tag publishes the bundle as a zip to install from; while developing, it is installed with `specify extension add --dev`.

### COMP-HOOKS Hooks and CI

Paths: `src/bondstone/hooks/`, `examples/`, `.pre-commit-hooks.yaml`\
Technology: Python, git hooks, Claude Code hooks, GitHub Actions\
Decided by: ADR-0006

`hooks install` writes the git pre-commit hook and, from 0.2, merges Claude Code hook entries into `.claude/settings.json` without touching other entries; `hooks run` is what they call. The pre-commit hook runs `check --staged` and the agent block from the trust model; projects that use the pre-commit framework use `.pre-commit-hooks.yaml` instead. The CI example runs the tests, then `check --all`, and `check --release` on release branches. spec-gates is optional and never a dependency; the recipe for running Bondstone as one of its gates is in `examples/`.

## Decisions

All six records are proposed and are written before this page is approved.

| ID | Decision | Components |
| --- | --- | --- |
| ADR-0001 | Python 3.11+ with Typer and uv; a measured Typer start-up of about 60 ms leaves room in the 1 s budget | COMP-CLI |
| ADR-0002 | Evidence comes from requirement IDs in test names, read from JUnit XML | COMP-EVIDENCE |
| ADR-0003 | Stages are computed every run; only approvals and `Verified:` lines are stored, with a versioned hash | COMP-STAGES, COMP-WRITE |
| ADR-0004 | A profile is a set of YAML packs; each requirement has one owner and is grouped by declared links | COMP-CONFIG, COMP-GRAPH, COMP-RULES |
| ADR-0005 | Spec Kit is the first host, plugged in through a host pack and a bundle | COMP-SPECKIT |
| ADR-0006 | Bondstone ships its own minimal hooks and a layered trust model; spec-gates is optional | COMP-WRITE, COMP-HOOKS |

## Repository layout

| Path | Holds |
| --- | --- |
| `src/bondstone/` | The CLI package, published to PyPI |
| `speckit/extension/`, `speckit/preset/` | The Spec Kit bundle, released under its own tag |
| `docs/` | The brief, this page, living specs (`docs/spec/`) and decisions (`docs/decisions/`) |
| `specs/` | Spec Kit change folders |
| `tests/` | Tests named after requirement IDs |
| `examples/` | The CI example and the spec-gates recipe |
| `.bondstone/` | Bondstone's own configuration |
| `.specify/`, `.claude/` | Files generated by `specify init`, `specify extension add` and `hooks install` |
| `AGENTS.md`, `CLAUDE.md` | The agent guide; `CLAUDE.md` imports `AGENTS.md` |
| `CHANGELOG.md` | One section per release |
| `LICENSE` | MIT |

The CLI and the bundle live in one repository so that a change to the JSON contract and the commands that read it land in one pull request. They are tagged separately (`cli-v0.1.0`, `speckit-v0.0.0`), and both version numbers follow the release they ship in.

## Open points

Proposed in this draft, to confirm before approval:

- `.bondstone/config.yml` as the configuration file.
- The tag names `cli-v*` and `speckit-v*`, with versions that follow the release.
- 200 documents as the repository size for the speed goal.
- A change counts as finished when every task in its `tasks.md` is ticked.
- `BRIEF` and `ARCH` as the IDs of the brief and this page.
- The spec's front-matter drops `release`: the brief's `Capabilities:` line is the one source.
