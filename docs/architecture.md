---
type: architecture
id: ARCH
title: Bondstone architecture
description: Context, quality goals, core concepts, documents, components, trust model and decisions of Bondstone, detailed for the current release.
status: draft
---

# Bondstone architecture

This page details what release 0.0 needs and outlines the rest. Each later component gets its section, paths and decisions when its release starts.

## Context

```mermaid
flowchart LR
  person([Person]) -- approves, verifies --> cli[[bondstone CLI]]
  agent([AI agent]) -- /speckit-bondstone-* --> ext[Spec Kit extension and preset]
  ext -- calls --> cli
  agent -- Claude Code hooks --> cli
  git[git pre-commit] -- check --staged --> cli
  ci([CI]) -- tests, then check --all --> cli
  cli -- reads --> repo[(docs, Spec Kit changes, tests, test reports, git index)]
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

These concepts are the core's whole vocabulary. Document names, ID prefixes, rules and stages come from the profile.

- **Item:** something with a stable ID: a document, a heading that starts with an ID, or a host's change folder.
- **Link:** a typed reference from one item to another, read only from item lines, change sections and front-matter fields. An ID in prose is never a link.
- **Owner:** every requirement has exactly one owner, the document it is written in.
- **Grouping:** a link type the profile declares to group requirements. The profile also names the *work unit*, which `next` names work on ("build GRAPH-1 to GRAPH-6"), and the *scope carrier*, whose release puts requirements in scope.
- **Release:** a planned delivery that the profile declares, with an order and one current release. A profile may declare none.
- **Scope:** a requirement is in scope when its release is the current one or comes before it. The requirement's own release wins over its scope carrier's; a requirement with neither is backlog. When the profile declares no releases, every requirement is in scope.
- **Stage:** a condition computed on every run, never stored.
- **Evidence:** a requirement's status: untested, linked, passing, failing or manual.
- **Approval:** a person's `status: stable`; from 0.2 also a `verified` record (see Documents).
- **Change:** a host's unit of work in progress. The host declares when a change is finished, choosing from conditions the core offers: every checkbox in a file is checked, a field has a given value, or the folder has moved. `next` works on the first unfinished change before anything but errors. A host whose changes finish another way needs a new condition in the core, but no new command.

In simple-app, a capability spec is the owner, the work unit and the scope carrier of its requirements, and a requirement's prefix equals its spec's ID. Releases are the brief's `REL-…` headings, in the brief's order, and its `release` field names the current one. A release's `Capabilities:` line gives each capability the release that starts it, even before its spec is written, and a requirement's `Release:` line overrides that.

## Documents

The documents in `docs/` form an Open Knowledge Format 0.2 bundle: every Markdown file there has front-matter with a non-empty `type`, and `index.md` and `log.md` are reserved. Bondstone adds `id` to OKF's `title`, `description` and `status`, as OKF allows, and uses OKF's status values: `draft`, `stable` for approved, and `deprecated`. A deprecated decision names its replacement in `superseded_by`. `README.md`, `AGENTS.md` and `CHANGELOG.md` stay outside the bundle.

From 0.2, `bondstone approve` records an approval as OKF's `verified` entry for a human reviewer, with Bondstone's hash as an extra field:

```yaml
status: stable
verified: {by: human:adam, at: 2026-11-02T10:00:00Z, hash: sha256-v1:…}
```

The hash covers the front-matter without `status` and `verified`, as JSON with sorted keys, and the body as UTF-8 with LF line endings, in Unicode NFC, without trailing whitespace and without `Verified:` lines. Comments, key order and manual verifications therefore never make an approval stale. A `Verified:` line under a `Check: manual` requirement records a manual check: the actor and the time, and from 0.2 a hash of the requirement's block.

## Components

### COMP-SPECKIT Spec Kit integration
Paths: `integrations/speckit/**` · Technology: a Spec Kit 1.2 extension and preset, Bash, Python · Decided by: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0007

Four agent commands with a wrapper script, and a preset that adds the `## Spec changes` section and test naming to Spec Kit's spec and tasks steps. Until 0.2, the extension also ships the stopgap and the pre-commit hook script. The extension and the preset each keep their manifest at the root of their own folder, `integrations/speckit/extension/` and `integrations/speckit/preset/`. The [SPECKIT spec](spec/speckit.md) states its behavior, and the stopgap applies the [PROFILE spec](spec/profile.md).

The CLI's components are designed when release 0.1 starts.

## Bootstrap

The extension's four commands keep their names from 0.0 (ADR-0007). In 0.0 the stopgap answers `check`, `status` and `next`, and `write` is a prompt. From 0.1 the CLI takes over what it can, and by 0.2 the stopgap is deleted; which CLI commands serve them is decided with each release.

## Trust model

Bondstone can't stop a determined agent. It makes an agent's approval hard to make by accident and impossible to hide (ADR-0004).

1. **From 0.0:** the pre-commit hook refuses staged changes to `status`, `verified` or `Verified:` lines when `CLAUDE_CODE_CHILD_SESSION` is set, as Claude Code does in the shells it runs.
2. **From 0.2:** `approve` and `verify` refuse to run in an agent's shell, or without a terminal unless `--yes` is given, and Claude Code hooks refuse agent calls to them and edits to those fields.
3. **In CI, from 0.1:** every check runs again, and changes to approvals show in the pull request's diff.

The hash detects staleness; it is not a signature. Evidence has the same limit: Bondstone proves that a test named after a requirement ran and passed, not that it tests the requirement.

## How Bondstone is tested

- Tests in `tests/` carry requirement IDs in their names, such as `test_SPECKIT_5_unfinished_adds_are_not_dangling`.
- Console examples in the specs run as tests. A pytest collector in `tests/conftest.py` runs each one in a fresh copy of `tests/fixtures/<name>/`, named by the block's `fixture=` option or the spec's `fixture` front-matter field, and names each result after its requirement.
- `pytest --junitxml=build/test-results/junit.xml` writes the report that the stopgap reads.

## Decisions

Each decision's status lives in its own front-matter. Later decisions are made when their release needs them.

| ID | Decision |
| --- | --- |
| [ADR-0001](decisions/0001-evidence-from-junit-test-names.md) | Read evidence from requirement IDs in JUnit test names |
| [ADR-0002](decisions/0002-computed-stages-stored-approvals.md) | Compute stages on every run and store only approvals |
| [ADR-0003](decisions/0003-spec-kit-first-host.md) | Make Spec Kit the first host |
| [ADR-0004](decisions/0004-own-hooks-layered-trust.md) | Ship minimal own hooks with a layered trust model |
| [ADR-0005](decisions/0005-living-spec-per-capability.md) | Keep one living spec per capability, changed in the same commit |
| [ADR-0006](decisions/0006-simple-app-profile.md) | Make simple-app the first profile |
| [ADR-0007](decisions/0007-extension-before-cli.md) | Ship the Spec Kit extension before the CLI |

## Repository layout

| Path | Holds |
| --- | --- |
| `docs/` | The OKF bundle: the brief, this page, specs (`docs/spec/`) and decisions (`docs/decisions/`) |
| `integrations/speckit/` | The Spec Kit extension and preset |
| `specs/` | Spec Kit change folders |
| `tests/` | Tests, the console-example collector and its fixtures |
| `.specify/`, `.claude/` | Files that `specify init` and `specify extension add` generate |
| `AGENTS.md`, `CLAUDE.md`, `README.md`, `CHANGELOG.md` | The agent guide, the readme and the changelog |
| `build/` | Test reports; not committed |
## Open points

To confirm before this page is approved:

- Specs have no `release` field; the brief's `Capabilities:` lines are the only source of a capability's release.
- The architecture page needs approval in the `shape` stage, like the specs.
- In 0.0 the profile has five rules and Spec Kit adds two; checks on ID shapes, components and code ownership are decided with 0.1.
