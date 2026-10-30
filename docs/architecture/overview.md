---
type: architecture
id: ARCH
title: Bondstone architecture
description: Context, quality goals, core concepts, documents, components, trust model and decisions of Bondstone, detailed for the current version.
status: draft
---

# Bondstone architecture

This page details what version 0.0 needs and outlines the rest. Each later component gets its section, paths and decisions when its version starts.

## Context

```mermaid
flowchart LR
  person([Person]) -- approves, verifies --> cli[[bondstone CLI]]
  agent([AI agent]) -- /speckit-bondstone-* --> ext[Spec Kit extension and preset]
  ext -- calls --> cli
  agent -- Claude Code hooks --> cli
  git[git pre-commit] -- check --staged --> cli
  ci([CI]) -- tests, then check --all --> cli
  cli -- reads --> repo[(living docs, plan/, Spec Kit folders, tests, test reports, git index)]
  cli -- writes --> out[(approvals, Verified lines, new documents, links)]
```

Bondstone never opens a network connection, calls a model, runs project code or reads production code. Until the CLI exists, a stopgap script stands in for it behind the extension's commands (see Bootstrap).

## Quality goals

| Goal | Measure |
| --- | --- |
| Deterministic | The same files give the same output, in every session |
| Fast | The pre-commit check finishes in under 1 s, start-up included |
| Visible approvals | Agents can't approve or verify through any supported path, and any other change to an approval shows in review |
| Host-agnostic | A second host needs no command change |
| Small | The extension's four commands keep their names in every release; larger profiles add packs, never commands |

## Core concepts

These concepts are the core's whole vocabulary. Document names, ID prefixes, rules and phases come from the profile.

- **Item:** something with a stable ID: a document, a heading that starts with an ID, or a host's change folder.
- **Link:** a typed reference from one item to another, read only from item lines, change sections and front-matter fields. An ID in prose is never a link.
- **Owner:** every requirement has exactly one owner, the document it is written in.
- **Grouping:** a link type the profile declares to group requirements. The profile also names the *work unit*, which `next` names work on ("build GRAPH-1 to GRAPH-6"), and the *scope carrier*, whose release puts requirements in scope.
- **Release:** a planned delivery that the profile declares, with an order and one current release. A profile may declare none.
- **Scope:** a requirement is in scope when its release is the current one or comes before it. The requirement's own release wins over its scope carrier's; a requirement with neither is backlog. When the profile declares no releases, every requirement is in scope.
- **Phase:** a condition computed on every run, never stored.
- **Evidence:** a requirement's status: untested, linked, passing, failing or manual.
- **Approval:** a person's `status: stable`; from 0.2 also a `verified` record (see Documents).
- **Change:** a host's unit of work in progress. The host declares when a change is finished, choosing from conditions the core offers: every checkbox in a file is checked, a field has a given value, or the folder has moved. `next` works on the first unfinished change before anything but errors. A host whose changes finish another way needs a new condition in the core, but no new command. A host supplies changes, their links and their finished state, never rules; the profile's rules decide how changes must relate to requirements.
- **Delta:** a change to requirements declared by a change doc above the host's changes: in simple-app, a version PRD's ADDED, MODIFIED, REMOVED, DEFERRED and DROPPED lines. Deltas land in living docs at a computed moment, on approval or with the story that changes the code.

In simple-app, a capability spec is the owner, the work unit and the scope carrier of its requirements, and a requirement's prefix equals its spec's ID. Releases are the roadmap's `V-…` versions, in the roadmap's order, and the first one not shipped is current. Every requirement carries its own `Release:` line; stories in a version PRD are the work units `next` hands out, one Spec Kit spec each. The [PROFILE capability](../capabilities/profile.md) states the layout, deltas and phases.

## Documents

The living docs in `docs/` form an Open Knowledge Format 0.2 bundle, and the change docs in `plan/` use the same front-matter: every Markdown file there has front-matter with a non-empty `type`, and `index.md` and `log.md` are reserved. Bondstone adds `id` to OKF's `title`, `description` and `status`, as OKF allows, and uses OKF's status values: `draft`, `stable` for approved, and `deprecated`. A deprecated decision names its replacement in `superseded_by`. `README.md`, `AGENTS.md` and `CHANGELOG.md` stay outside the bundle.

From 0.2, `bondstone approve` records an approval as OKF's `verified` entry for a human reviewer, with Bondstone's hash as an extra field:

```yaml
status: stable
verified: {by: human:adam, at: 2026-11-02T10:00:00Z, hash: sha256-v1:…}
```

The hash covers the front-matter without `status` and `verified`, as JSON with sorted keys, and the body as UTF-8 with LF line endings, in Unicode NFC, without trailing whitespace and without `Verified:` lines. Comments, key order and manual verifications therefore never make an approval stale. A `Verified:` line under a `Check: manual` requirement records a manual check: the actor and the time, and from 0.2 a hash of the requirement's block.

## Components

### COMP-SPECKIT Spec Kit integration
Paths: `integrations/speckit/**` · Technology: a Spec Kit 1.2 extension and preset, Bash, Python · Decided by: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0007, ADR-0008

Four agent commands with a wrapper script and a template for every living and change doc, and a preset that makes each Spec Kit spec one story (front-matter `story` and `proves`), adds `## Expected living-doc impact` to the plan and `## Living doc changes` to the spec, and makes example-named tests and the living-doc update tasks. Until 0.2, the extension also ships the stopgap (`scripts/python/bondstone_stopgap.py`, standard library only) and the pre-commit hook script. The extension and the preset each keep their manifest at the root of their own folder, `integrations/speckit/extension/` and `integrations/speckit/preset/`. The [SPECKIT capability](../capabilities/speckit.md) states its behavior, and the stopgap applies the [PROFILE capability](../capabilities/profile.md).

The CLI's components are designed when release 0.1 starts.

## Bootstrap

The extension's four commands keep their names from 0.0 (ADR-0007). In 0.0 the stopgap answers `check`, `status` and `next`, and `write` is a prompt. From 0.1 the CLI takes over what it can, and by 0.2 the stopgap is deleted; which CLI commands serve them is decided with each release.

## Trust model

Bondstone can't stop a determined agent. It makes an agent's approval hard to make by accident and impossible to hide (ADR-0004).

1. **From 0.0:** the pre-commit hook refuses staged lines that add or remove an approval (`status: stable` or `deprecated`, `verified:`, `Verified:`, a version's `Status: shipped`) when `CLAUDE_CODE_CHILD_SESSION` is set, as Claude Code does in the shells it runs.
2. **From 0.2:** `approve` and `verify` refuse to run in an agent's shell, or without a terminal unless `--yes` is given, and Claude Code hooks refuse agent calls to them and edits to those fields.
3. **In CI, from 0.1:** every check runs again, and changes to approvals show in the pull request's diff.

The hash detects staleness; it is not a signature. Evidence has the same limit: Bondstone proves that a test named after a requirement ran and passed, not that it tests the requirement.

## How Bondstone is tested

- Tests in `tests/` carry example IDs in their names, such as `test_PROFILE_6_1_added_lands_at_approval`. Helpers in `tests/conftest.py` build small simple-app projects in a temporary folder and run the stopgap on them.
- `tests/fixtures/habit-app/` is a mid-build example project for demos and smoke tests; pytest does not collect it.
- `pytest --junitxml=build/test-results/junit.xml` writes the report that the stopgap reads.

## Decisions

Each decision's status lives in its own front-matter. Later decisions are made when their release needs them.

| ID | Decision |
| --- | --- |
| [ADR-0001](../decisions/0001-evidence-from-junit-test-names.md) | Read evidence from requirement IDs in JUnit test names |
| [ADR-0002](../decisions/0002-computed-stages-stored-approvals.md) | Compute stages on every run and store only approvals |
| [ADR-0003](../decisions/0003-spec-kit-first-host.md) | Make Spec Kit the first host |
| [ADR-0004](../decisions/0004-own-hooks-layered-trust.md) | Ship minimal own hooks with a layered trust model |
| [ADR-0005](../decisions/0005-living-spec-per-capability.md) | Keep one living spec per capability, changed in the same commit |
| [ADR-0006](../decisions/0006-simple-app-profile.md) | Make simple-app the first profile |
| [ADR-0007](../decisions/0007-extension-before-cli.md) | Ship the Spec Kit extension before the CLI |
| [ADR-0008](../decisions/0008-simple-app-workflow.md) | Run simple-app as living docs, version PRDs and stories as Spec Kit specs |

## Repository layout

| Path | Holds |
| --- | --- |
| `docs/` | Living docs, an OKF bundle: brief, roadmap, idea inbox, glossary, this page (`docs/architecture/`), capability specs (`docs/capabilities/`) and decisions (`docs/decisions/`) |
| `plan/` | Change docs for the active version: its PRD, optional epics and release checklist; `plan/archive/` holds shipped versions |
| `integrations/speckit/` | The Spec Kit extension and preset |
| `specs/` | Spec Kit folders, one per story |
| `tests/` | Tests, their helpers and fixtures |
| `.specify/`, `.claude/` | Files that `specify init` and `specify extension add` generate |
| `AGENTS.md`, `CLAUDE.md`, `README.md`, `CHANGELOG.md` | The agent guide, the readme and the changelog |
| `build/` | Test reports; not committed |

## Open points

To confirm before this page is approved:

- Every requirement carries its own `Release:` line; the roadmap's `Capabilities:` lines are informational.
- The architecture overview needs approval in Shape, with the roadmap and the first PRD.
- Console examples (trycmd) are not an example form in 0.0; examples are WHEN/THEN lines with scoped IDs.
- Checks on components and code ownership are decided with 0.1.
