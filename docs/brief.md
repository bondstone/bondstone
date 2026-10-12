---
type: brief
id: BRIEF
title: Bondstone
description: A deterministic CLI and Spec Kit extension that says which approved requirements are proven by passing tests, and what to do next.
status: draft
release: REL-0.0
---

# Bondstone

## Problem

A solo developer is building a mobile app with Claude Code and GitHub Spec Kit. On day twelve they open a new session to add photo uploads. The agent doesn't know that offline sync was redesigned last week, because that decision lived in a closed chat and in a spec folder nobody reads any more, so it writes a second sync path. The acceptance criteria in `specs/004-sync` no longer describe what the app does, and neither the developer nor the agent can say which requirements are still proven by a passing test.

Spec Kit asks agents to follow the process; nothing checks that they did. And an agent that grades its own work makes every gate meaningless.

## Users

- **User zero:** the maintainer, building Bondstone itself with Claude Code and Spec Kit, and through Bondstone from release 0.0.
- **Next:** solo developers building real products, such as a mobile app, with a coding agent.

## Goals

**In 90 days**

- Release 0.2 with Bondstone's own repository passing its release gate.
- Say, for every requirement, whether it is untested, linked, passing, failing or manually checked.
- Compute the project's stage and one next step on every run, identically in every session.
- Keep the pre-commit check under 1 s.

**Within a year**

- A second host integration (BMAD or OpenSpec) works without changing any command.
- A team profile is used by at least one team other than user zero.
- Bondstone is listed in the Spec Kit community catalog.

## Principles

- **You approve behavior, tests prove it, Bondstone computes the rest.**
- Deterministic: no network, no AI; the same inputs always give the same answer.
- Only a person approves or verifies; hooks block agents from both.
- Evidence is a passing test whose name carries the requirement ID, read from JUnit XML; production code is never read.
- Stages are computed, never stored; only approvals, `Verified:` lines and the session focus are stored.
- Approved behavior lives in current documents with stable requirement IDs; a change isn't finished until those documents reflect it.
- A profile is a set of YAML packs; larger profiles add packs, never commands.
- The core stays host-agnostic; Spec Kit is the first host, behind an adapter.

## Releases

Three releases, about 25 focused days, each built with the one before. Each command keeps its name from 0.0 on; only its body moves from the bootstrap to the CLI, so nothing migrates.

### REL-0.0 Bootstrap

Capabilities: SPECKIT
Appetite: 3 focused days

The Spec Kit preset and the extension's four commands, in their final form. `check` and `status` run a stopgap script that applies the simple-app rules and reads the JUnit report; `next` and `write` are prompts. Approvals are made by setting `status` by hand. A pre-commit hook runs the stopgap check.

**No-gos:** the CLI and its PyPI package, recorded approvals, Claude Code hooks, CI.

### REL-0.1 Checker

Capabilities: GRAPH, PROFILE, CHECK, EVIDENCE, SETUP
Appetite: 12 focused days

Built through the bootstrap. The extension's `check` runs `bondstone check`, the stopgap script is deleted, and the CLI is published to PyPI. Includes `init`, the pre-commit hook, a CI example and the spec-gates recipe.

**No-gos:** CLI-backed `status`, `next` and `write`, `approve` and `verify`, manual checks, Claude Code hooks, the release gate.

### REL-0.2 Agent loop

Capabilities: WRITE, APPROVE, FLOW
Appetite: 10 focused days

`status`, `next` and `write` call the CLI. Approvals are recorded with an actor, time and hash. Adds profile stages, manual checks, Claude Code hooks and the release gate; 0.2 gates its own release.

**No-gos:** team features, Windows, impact reports, an MCP server.

## Later

Not scheduled. Each arrives as a profile, pack, template or host integration, without new commands.

- **Users:** small teams sharing one repository and one set of rules; later, organizations that need portfolio, architecture and change governance on the same documents.
- **Profiles:** team and enterprise, including stories, sprints, portfolio stages and separate building-block items.
- **Packs:** release, mobile store, use cases, and compatibility with the consolidated spec written by spec-kit-archive.
- **Hosts:** BMAD and OpenSpec.
- **Features:** an impact report, Windows support, an MCP server.

## Alternatives

| Tool | What it does | How Bondstone differs |
| --- | --- | --- |
| [DocGuard](https://github.com/raccioly/docguard) | A large Node.js CLI that keeps a fixed set of canonical documents in step with code, with 30+ validators; it traces requirement IDs to tests by their presence in test files | One configurable graph instead of fixed documents; pass or fail per requirement from test reports; a computed next step; a small profile |
| [spec-gates](https://github.com/schwichtgit/spec-gates) | Runs one quality gate identically at Claude Code hooks, git hooks and CI | Complementary: Bondstone can run as one of its gates |
| [spec-kit-archive](https://github.com/stn1slv/spec-kit-archive) | An agent merges each finished feature spec into one project spec after the merge | Bondstone checks deterministically that every finished change is reflected in the current documents; a compatibility pack may come later |
| [spec-kit-trace](https://github.com/Quratulain-bilal/spec-kit-trace) | An agent prompt that builds a requirement-to-test matrix | Bondstone computes the matrix in code from test results |
