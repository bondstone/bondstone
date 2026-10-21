---
type: architecture
id: ARCH
title: Bondstone architecture
description: Context, quality goals, core concepts, components, flows, contracts, decisions and risks of the Bondstone CLI and its integrations.
status: draft
---

# Bondstone architecture

## Context

```mermaid
flowchart LR
  person([Person]) -- approves, verifies --> cli[[bondstone CLI]]
  agent([AI agent]) -- /speckit-bondstone-* --> ext[Spec Kit extension and preset]
  ext -- calls --> cli
  agent -- Claude Code hooks --> cli
  git[git pre-commit] -- hooks run pre-commit --> cli
  ci([CI]) -- tests, then check --all --> cli
  gates[spec-gates, optional] -- custom gate --> cli
  cli -- reads --> repo[(docs, Spec Kit changes, tests, test reports, git index)]
  cli -- writes --> out[(approvals, Verified lines, new documents, links)]
```

Until the CLI takes over, a stopgap script stands in for it behind the extension's commands (see Bootstrap).

| Interface | Contract |
| --- | --- |
| Commands | `init`, `hooks install`, `hooks run`, `check`, `status`, `next`, `context`, `new`, `id next`, `link`, `approve`, `verify`, `version` |
| Exit codes | 0 success · 1 error violations or a refused approval · 2 configuration or usage error · 3 internal error. `hooks run` follows the host's hook protocol instead, and `status`, `next` and `context` exit with 0 unless they cannot run |
| JSON | `--json` prints exactly one object with `schema_version`; a breaking change bumps it. On exit code 2 or 3, the object has only `schema_version` and `error` |
| Reads | Markdown under the configured paths, host change folders, test files (plain-text search), JUnit XML reports, the git file list and index, hook input on stdin |
| Writes | `init` writes `.bondstone/rules.yml` and a block in `AGENTS.md`; `hooks install` writes the git pre-commit hook; `new`, `link`, `approve` and `verify` change only the document they are named for |
| Never | Network access, model calls, running project code, reading the content of production source files |

## Quality goals

| Goal | Measure |
| --- | --- |
| Deterministic | The same files give byte-identical output; golden-file tests cover every rule |
| Fast | On a generated 500-document repository, `check --staged` under 1 s and `check --all` under 3 s, start-up included (CHECK-10) |
| Safe | `rules.yml` and packs are data, loaded strictly and safely; test reports are parsed without expanding entities |
| Non-destructive | Writers change only the lines they own; round-trip tests cover every writer |
| Visible approvals | Agents cannot approve or verify through any supported path, and any other change to an approval shows in review |
| Host-agnostic | A second host needs a host pack and its own integration, never a command change |
| Small | 13 commands; the simple-app profile has 5 document types and 10 rules |
| Portable | macOS and Linux with Python 3.11 or later; native Windows is untested until a later release |

## Core concepts

The core knows only these concepts. Document names, ID prefixes, rules and stages come from the profile's packs.

- **Item:** something with a stable ID: a document, a heading that starts with an ID, a list item where a pack allows it, or a host's change folder.
- **Type:** declared by a pack, with an ID pattern, where its items are found, and which item lines, link sections and front-matter relations they carry.
- **Link:** a typed reference from one item to another, read only from item lines, link sections, front-matter relations and nesting. An ID in prose is never a link, and reverse links are computed, never stored.
- **Owner:** every requirement has exactly one owner, the document it is written in.
- **Grouping:** a link type the profile declares to group requirements. The profile also names the *work unit*, the type that `next` names work on ("build GRAPH-1 to GRAPH-6"), and the *scope carrier*, the type whose release puts requirements in scope.
- **Scope:** a requirement is in scope when its release is the current release or an earlier one, in the order the brief declares them. Its own `Release:` line wins over its scope carrier's release; a requirement with neither is backlog.
- **Stage:** a condition the profile computes on every run. A stage names the items it needs approved as selectors, so the same mechanism covers one document or many.
- **Evidence:** a requirement's status: untested, linked, passing, failing or manual.
- **Approval:** a person's `status` change, plus, from 0.2, a `verified` record with the actor, the time and a hash.
- **Change:** a host's unit of work in progress, such as a Spec Kit feature folder. The host pack declares when a change is finished, choosing from the conditions the core offers: every checkbox in a declared file is checked, a declared field has a given value, or the change folder has moved under a declared path. `next` works on the first unfinished change, in ID order, before anything but errors. A host whose changes finish in another way needs a new condition in the core and a new pack schema version, but no new command.

In the simple-app profile, a capability spec is the owner, the work unit and the scope carrier of its requirements, and a requirement's prefix equals its spec's ID; that last rule belongs to simple-app, not to the core. The brief's `Capabilities:` line gives each capability the release that starts it, and may name capabilities whose specs aren't written yet. The [PROFILE spec](spec/profile.md) has the details.

## Components

Data flows one way: configuration, then the graph, then evidence, then rules, then stages; the command layer renders the result. Writers and hooks sit beside that flow and call into it, and only writers change documents. Together, the components' `Paths` cover every file under `src/` and `integrations/`.

### COMP-CLI Command layer
Paths: `src/bondstone/*.py`, `src/bondstone/cli/**`, `pyproject.toml`, `uv.lock` · Technology: Python 3.11+, Typer, uv · Decided by: ADR-0001

Parses arguments and scopes, renders text and JSON, and maps outcomes to exit codes. It knows no document type, rule or pack. Commands import only what they use, and the hook path never loads Rich, so start-up stays under 150 ms.

### COMP-CONFIG Configuration and packs
Paths: `src/bondstone/config/**`, `src/bondstone/packs/**` · Technology: a strict, safe YAML loader, JSON Schema · Decided by: ADR-0004

Loads `.bondstone/rules.yml` and the packs it names, merges their types, relations, stages and rules, applies overrides, and validates everything before any scan. YAML that would construct objects is rejected. The shipped packs, `simple-app` and the `speckit` host pack, are data in this component, with their templates and guidance files; no pack contains code.

### COMP-GRAPH Document graph
Paths: `src/bondstone/graph/**` · Technology: a line scanner aware of code fences, the strict YAML loader for front-matter, git for the file list and the index · Decided by: ADR-0004

Builds the typed graph of items and links from documents, host change folders and the file list, reading the git index for `--staged`, and answers forward, reverse and neighbourhood queries. Parses 500 documents in under 300 ms, and reports malformed input as findings instead of failing.

### COMP-RULES Rule engine
Paths: `src/bondstone/rules/**` · Technology: Python evaluators for declarative rules, plus parameterized built-in checks · Decided by: ADR-0004

Evaluates the active rules for a scope and returns violations and review signals in a fixed order: file, line, rule. Skips, and lists, the rules that refer to undeclared types or need a missing test report. Under `--release`, evidence gaps and missing or stale approvals become errors.

### COMP-EVIDENCE Test evidence
Paths: `src/bondstone/evidence/**` · Technology: defusedxml for JUnit XML, token patterns compiled from the declared capability prefixes · Decided by: ADR-0002

Turns test reports and test files into one evidence status per requirement: untested, linked, passing, failing or manual. Never reads the content of production source files.

### COMP-STAGES Stages and flow
Paths: `src/bondstone/stages/**` · Technology: Python, SHA-256 · Decided by: ADR-0003

Computes stages, approval freshness, the next action, `status` and `context` from the graph, the evidence and the approvals. Stores nothing.

### COMP-WRITE Writers
Paths: `src/bondstone/write/**` · Technology: ruamel.yaml round trips, line-level patching · Decided by: ADR-0003, ADR-0006

Creates documents from the packs' templates, finds the next free ID, adds links, and writes approvals and verifications. Leaves every byte it does not own unchanged. `approve` and `verify` refuse to run in an agent's shell.

### COMP-SPECKIT Spec Kit integration
Paths: `integrations/speckit/**` · Technology: a Spec Kit extension and preset for Spec Kit 1.2 or later below 2.0, Bash, Python · Decided by: ADR-0005, ADR-0010

Four agent commands with a wrapper script that calls the CLI, and a preset that adds the `## Spec changes` section and test naming to Spec Kit's spec and tasks steps. Until 0.2, the extension also ships the stopgap and its pre-commit hook script. The extension and the preset each keep their manifest at the root of their own folder, `integrations/speckit/extension/` and `integrations/speckit/preset/`.

### COMP-HOOKS Hooks and CI
Paths: `src/bondstone/hooks/**`, `integrations/claude-code/**`, `integrations/git/**`, `integrations/ci/**` · Technology: Python, a git hook script, Claude Code hook configuration, a GitHub Actions workflow, a spec-gates policy entry · Decided by: ADR-0006

Installs and runs the hooks that apply the same check at the agent, commit and CI boundaries, load context at session start, and keep approvals human. `hooks run` translates between a host's hook protocol and Bondstone's exit codes. spec-gates stays optional: `hooks install --gates` prints its policy entry.

## Bootstrap

The extension's four commands keep their names from 0.0; what runs behind them moves to the CLI over three releases (ADR-0010).

| Behind | 0.0 | 0.1 | 0.2 |
| --- | --- | --- | --- |
| `check` | Stopgap | `bondstone check` | `bondstone check` |
| `status`, `next` | Stopgap | Stopgap, reading `bondstone check --json` | `bondstone status`, `bondstone next` |
| `write` | Prompt | Prompt | Prompt calling `new`, `id next` and `link` |
| Pre-commit hook | Stopgap check and the agent block | `bondstone hooks run pre-commit` | `bondstone hooks run pre-commit` |

The stopgap computes statuses, the stage and the next step itself, in the CLI's formats, so every command relays output from 0.0 on and the agent never computes a step. Until `approve` exists, it counts a bare `status` of `stable` or `accepted` as a current approval (SPECKIT-5). It is deleted in 0.2.

## Key flows

1. **Commit.** The pre-commit hook runs `check --staged` and the agent block. Errors refuse the commit; warnings and review signals don't.
2. **Session.** From 0.2, the SessionStart hook prints `bondstone context --brief`. `/speckit-bondstone-next` names one action; the agent loads its context and does it. When the agent tries to stop, the Stop hook keeps it working while its uncommitted changes have errors.
3. **Build.** For one or two open requirements, the agent changes the living spec, a test named with the requirement's ID, and the code in one commit. For three or more in one capability, `next` suggests a Spec Kit change whose `## Spec changes` section lists their IDs under `Implements:`.
4. **Release.** CI runs the tests with a JUnit report, then `bondstone check --all --release`, which fails on any in-scope requirement without passing evidence, any missing or stale approval, or a missing changelog section.

## Stored state

Bondstone stores only what a person decides; stages, progress and the backlog are computed.

| What | Where | Written by |
| --- | --- | --- |
| Approval | `status` in the approved document's front-matter, and from 0.2 `verified`: the actor, the time and a hash | A person sets `status`; from 0.2, `approve` writes both |
| Manual check | A `Verified:` item line under a `Check: manual` requirement: the actor, the time and, from 0.2, a hash | A person until 0.2, then `verify` |
| Retired IDs | The `retired` list in a spec's front-matter | A person, when a requirement is removed |

An approval's hash covers a canonical form of the document: its front-matter without `status` and `verified`, as JSON with sorted keys, then its body as UTF-8 without a byte-order mark, with LF line endings, in Unicode NFC, without trailing whitespace and without `Verified:` lines. Comments, key order and verifications therefore never make an approval stale. A verification hashes its requirement's block the same way. Hashes carry a version prefix, `sha256-v1:`, and Bondstone keeps checking earlier versions (APPROVE-4, APPROVE-5). Times are quoted RFC 3339 strings in UTC.

## Trust model

Bondstone cannot stop a determined agent. It makes an agent's approval hard to make by accident and impossible to hide (ADR-0006).

1. **From 0.0:** the pre-commit hook refuses staged changes to `status`, `verified` or `Verified:` lines when `CLAUDE_CODE_CHILD_SESSION` is set, as Claude Code does in the shells it runs.
2. **From 0.2:** `approve` and `verify` refuse to run without a terminal unless `--yes` is given, and always in an agent's shell. Claude Code's PreToolUse hook refuses Bash calls to both commands, and edits that would change those fields.
3. **In CI:** `check --all --release` re-checks every hash, and changes to approvals, `rules.yml` and hook settings show in the pull request's diff. `git commit --no-verify` doesn't skip CI.

The hash detects staleness; it is not a signature. An agent with shell access, or an agent outside Claude Code, can still write a valid record, and the person sees it in review. Evidence has the same limit: Bondstone proves that a test named after a requirement ran and passed, not that it tests the requirement. Console examples that run as tests close part of that gap.

## Contracts

- **Configuration:** `.bondstone/rules.yml` and every pack start with `bondstone: 1`. A version this CLI doesn't know, a schema error, or YAML that would construct objects exits with 2 before anything is evaluated (CHECK-7). YAML is loaded strictly: duplicate keys are rejected, and no value becomes a date, or a boolean other than `true` or `false`.
- **Integrations:** each integration declares the minimum CLI version it needs. The Spec Kit wrapper script checks `bondstone version --json` and stops with an install instruction when the CLI is missing or too old (SPECKIT-10, SETUP-6). The extension and the preset need Spec Kit `>=1.2.0,<2.0.0`.

## Determinism

Output is a pure function of the files Bondstone reads. Violations sort by file, line and rule, and requirement lists by natural ID order (`SYNC-2` before `SYNC-10`). Paths are POSIX and relative to the repository root. Output carries no wall-clock time, absolute paths, durations or environment details. There is no persistent cache. Only `approve` and `verify` record a time, on purpose.

## How we verify Bondstone

- Tests in `tests/` carry requirement IDs in their names, for example `test_CHECK_3_json_is_one_object`.
- Console examples in `docs/spec/*.md` run as tests. A pytest collector in `tests/conftest.py` runs each example in a fresh copy of `tests/fixtures/<name>/`, where the name comes from the block's `fixture=` option or the spec's `fixture` front-matter field, and names each result after its requirement.
- `pytest --junitxml=build/test-results/junit.xml` writes the report. In 0.0 the stopgap reads it; from 0.1, CI runs `bondstone check --all` on this repository.
- A generated 500-document repository is the performance benchmark (CHECK-10).

## Decisions

Each decision's status lives only in its own front-matter.

| ID | Decision |
| --- | --- |
| [ADR-0001](decisions/0001-python-typer-uv.md) | Build the CLI in Python with Typer and uv |
| [ADR-0002](decisions/0002-evidence-from-junit-test-names.md) | Read evidence from requirement IDs in JUnit test names |
| [ADR-0003](decisions/0003-computed-stages-stored-approvals.md) | Compute stages on every run and store only approvals |
| [ADR-0004](decisions/0004-profiles-as-yaml-packs.md) | Define profiles as YAML packs over a small core |
| [ADR-0005](decisions/0005-spec-kit-first-host.md) | Make Spec Kit the first host, plugged in through a host pack |
| [ADR-0006](decisions/0006-own-hooks-layered-trust.md) | Ship minimal own hooks with a layered trust model |
| [ADR-0007](decisions/0007-one-repository.md) | Keep the CLI and its integrations in one repository |
| [ADR-0008](decisions/0008-living-spec-per-capability.md) | Keep one living spec per capability, changed in the same commit |
| [ADR-0009](decisions/0009-simple-app-profile.md) | Make simple-app the first profile |
| [ADR-0010](decisions/0010-extension-before-cli.md) | Ship the Spec Kit extension before the CLI |

## Repository layout

| Path | Holds |
| --- | --- |
| `src/bondstone/` | The CLI package, published to PyPI, with the shipped packs in `packs/` |
| `integrations/speckit/` | The Spec Kit extension and preset |
| `integrations/claude-code/`, `integrations/git/`, `integrations/ci/` | Claude Code hook configuration, the git hook script and the example CI workflow |
| `docs/` | The brief, this page, living specs (`docs/spec/`) and decisions (`docs/decisions/`) |
| `specs/` | Spec Kit change folders |
| `tests/` | Tests named after requirement IDs, the console-example collector and its fixtures |
| `.bondstone/rules.yml` | Bondstone's configuration for this repository |
| `.specify/`, `.claude/` | Files that `specify init` and `specify extension add` generate |
| `AGENTS.md`, `CLAUDE.md` | The agent guide; `CLAUDE.md` imports `AGENTS.md` |
| `CHANGELOG.md` | One section per release |
| `build/` | Test reports; not committed |

The CLI and its integrations share one repository and are released with separate tags: `bondstone-vX.Y.Z` for the CLI and `speckit-vX.Y.Z` for the extension and preset (ADR-0007).

## Risks

- **Test-name discipline in other languages.** Some reporters drop display names or rewrite names. Mitigated by per-style declaration patterns, naming conventions in the templates, and the `not-reported` review signal.
- **Requirement sprawl.** Living specs can grow. Keep requirements at observable behavior, about 5 to 15 per capability.
- **Agents ignoring template guidance.** Measured during dogfooding. The fallback is one mandatory Spec Kit hook that points at `/speckit-bondstone-next`.
- **The stopgap outliving its release.** It duplicates part of CHECK and FLOW; SPECKIT-11 removes it in 0.2.
- **Duplicate IDs from parallel branches.** `id next` counts the `Adds:` lines of unfinished changes, and `unique-ids` catches the rest at merge; a renumbering helper may be needed later.
- **Spec Kit's pace.** Releases arrive often. The extension pins `>=1.2.0,<2.0.0`, and CI tests the install against new versions.

## Open points

To confirm before this page is approved:

- Specs have no `release` field; the brief's `Capabilities:` lines are the only source of a capability's release (PROFILE-6).
- The architecture page is approved like a spec, and the `shape` stage needs that approval (PROFILE-11).
- The stopgap applies seven of the ten rules; `valid-ids`, `component-complete` and `code-has-owner` wait for `bondstone check` in 0.1 (SPECKIT-4).
- Front-matter isn't claimed to be compatible with Open Knowledge Format v0.2: decisions use MADR's `proposed` and `accepted`, which OKF's `status` doesn't define, and OKF has its own `verified` key.
