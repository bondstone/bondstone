---
type: brief
id: BRIEF
title: Bondstone
description: A deterministic CLI, with a Spec Kit extension and preset, that says which approved requirements are proven by passing tests, and what to do next.
status: draft
release: REL-0.0
---

# Bondstone

## Problem

A solo developer is building a mobile app with Claude Code and GitHub Spec Kit. On day twelve they open a new session to add photo uploads. The agent doesn't know that offline sync was redesigned last week, because that decision lived in a closed chat and in a spec folder nobody reads any more, so it writes a second sync path. The acceptance criteria in `specs/004-sync` no longer describe what the app does, and neither the developer nor the agent can say which requirements are still proven by a passing test.

Spec Kit asks agents to follow the process. The checks built around it look for requirement IDs in files or run linters; none says, from test results, which approved requirements still pass, or what to do next. And an agent that grades its own work makes every gate meaningless, whether it approves its own spec or names an empty test after a requirement.

With Bondstone, the sync redesign could not have been finished until the current sync spec reflected it. The next session would have started from that spec, and `status` would have shown which sync requirements still pass. Bondstone would not have spotted the second sync path itself: it never reads production code.

## Users

- **User zero:** the maintainer, building Bondstone itself with Claude Code and Spec Kit, and through Bondstone from release 0.0.
- **Next:** solo developers building real products, such as a mobile app, with a coding agent and a test runner that can write JUnit XML.

## Terms

- **Requirement:** an approved behavior with a stable ID, such as `SYNC-2`, and at least one example.
- **Evidence status:** untested, linked (tests exist, no result yet), passing, failing or manual.
- **Stage:** where the project stands (frame, shape, build or release), computed from the documents and test results.
- **Profile and pack:** a profile is the set of documents, IDs, rules and stages a project uses, made of YAML packs; simple-app is the first.
- **Host:** the spec workflow Bondstone plugs into; Spec Kit is the first.
- **Appetite:** the time a release may take; scope shrinks to fit it.

## Goals

**In 90 days**

- Release 0.2 with Bondstone's own repository passing its release gate.
- Give every requirement its evidence status.
- Compute the project's stage and one next step on every run, identically in every session, from release 0.0.
- `next` names the right step in at least 9 of 10 logged sessions.
- Keep the pre-commit check under 1 s, start-up included.

**Within a year**

- A second host integration (BMAD or OpenSpec) works without changing any command.
- A team profile is used by at least one team other than user zero.
- Ten repositories other than Bondstone's run `bondstone check` in CI.
- The Bondstone extension and preset are listed in the Spec Kit community catalog.

## Principles

- **You approve behavior, tests prove it, Bondstone computes the rest.**
- Deterministic: no network, no AI; the same inputs always give the same answer.
- Only a person approves or verifies. Hooks stop agents from doing either, and CI shows any change that gets past them.
- Evidence is a passing test whose name carries the requirement ID, read from JUnit XML; production code is never read. A test name is a claim the person reviews: Bondstone proves the test ran and passed, not that it tests the requirement.
- Stages are computed, never stored; only approvals and `Verified:` lines are stored.
- Approved behavior lives in current documents with stable requirement IDs; a change isn't finished until those documents reflect it.
- A profile is a set of YAML packs; larger profiles add packs, never commands.
- The core stays host-agnostic; Spec Kit is the first host, kept outside the core.

## Releases

Three releases, about 27 focused days, each built with the one before. Each of the extension's four commands (`status`, `next`, `write`, `check`) keeps its name from 0.0 on; only its body moves from the bootstrap to the CLI, so nothing migrates. A capability is listed under the release that starts it; requirements that land later carry their own `Release:` line. Moving the brief to the next release makes its approval stale, on purpose: each release re-confirms the frame.

### REL-0.0 Bootstrap
Capabilities: SPECKIT, PROFILE · Appetite: 5 focused days

The Spec Kit extension and preset, with the four commands under their final names. A stopgap script applies the simple-app rules for IDs, links, examples, evidence and changes, reads the JUnit report, and computes each requirement's status, the stage and the next step as JSON. `check`, `status` and `next` relay its output; `write` is a prompt. Approvals are made by setting `status` by hand, and manual checks by writing a `Verified:` line by hand. A pre-commit hook runs the stopgap check and rejects changes to `status`, `verified` or `Verified:` lines made from an agent's shell. Each session is logged with whether `next` was right.

**No-gos:** the CLI and its PyPI package, recorded approvals, Claude Code hooks, CI.

### REL-0.1 Checker
Capabilities: GRAPH, CHECK, EVIDENCE, SETUP · Appetite: 12 focused days

Built through the bootstrap. The extension's `check` runs `bondstone check`, and the CLI is published to PyPI. The stopgap keeps only the stage and the next step, computed from `bondstone check --json`. Includes `init`, the pre-commit hook, a CI example and the spec-gates recipe.

**No-gos:** CLI-backed `status`, `next` and `write`, `approve` and `verify`, Claude Code hooks, the release gate.

### REL-0.2 Agent loop
Capabilities: WRITE, APPROVE, FLOW · Appetite: 10 focused days

`status`, `next` and `write` call the CLI, and the stopgap script is deleted. `approve` and `verify` record approvals and manual checks with an actor, time and hash, and refuse to run from an agent's shell. Adds profile stages, Claude Code hooks and the release gate; 0.2 gates its own release.

**No-gos:** team features, native Windows, impact reports, an MCP server.

## Risks

- **Agents don't follow the flow.** This is the riskiest assumption, and 0.0 exists to test it. The session log records whether the agent started from `next`, stayed on its step, named tests after IDs and filled in `## Spec changes`. If it follows the step unprompted in fewer than 8 of 10 sessions, the flow is rethought before 0.2.
- **Empty tests.** An agent can name a test after a requirement and assert nothing. Console examples run as tests, and the person reviews test names; Bondstone does not judge test quality.
- **Spec Kit moves fast.** Version 0.10 removed `init` flags, and Claude now installs its commands as skills. The extension pins the Spec Kit versions it supports, and CI runs an install smoke test.
- **Appetite.** 0.0 holds 18 requirements in 5 days, and 0.1 about 50 in 12. If 0.1 runs out of time, the spec-gates recipe goes first, then the CI example.

## Later

Not scheduled. Profiles, packs, templates and hosts arrive without new commands; only the features in the last line may add one.

- **Users:** small teams sharing one repository and one set of rules; later, organizations that need portfolio, architecture and change governance on the same documents.
- **Profiles:** team and enterprise, including stories, sprints, portfolio stages and separate building-block items.
- **Packs:** release, mobile store, use cases, and compatibility with the consolidated spec written by spec-kit-archive.
- **Hosts:** BMAD and OpenSpec.
- **Features:** an impact report, native Windows support, an MCP server.

## Alternatives

| Tool | What it does | How Bondstone differs |
| --- | --- | --- |
| [DocGuard](https://github.com/raccioly/docguard) | A Node.js CLI and Spec Kit extension with 34 validators, starter to enterprise profiles, a living-spec registry and an MCP server; it links requirement IDs to test declarations in test files | Pass or fail per requirement from test results, not mentions; person-only, hash-pinned approvals; one computed next step |
| [SpecAssay](https://github.com/rdryfoos/specassay) | A deterministic Spec Kit gate that finds acceptance-criterion IDs in test names | Reads whether those tests passed, and computes a stage and next step |
| [spec-validate](https://github.com/aeltayeb/spec-kit-spec-validate) | A Spec Kit extension that gates reviews and keeps hook-enforced approval state with a SHA-256 hash | Overlaps on approvals; Bondstone ties them to test evidence and stages |
| [spec-gates](https://github.com/schwichtgit/spec-gates) | Runs one quality gate identically at Claude Code hooks, git hooks and CI; also runs acceptance checks and requires approval trailers on protected files | Complementary, with some overlap on approvals: Bondstone can run as one of its gates |
| [spec-kit-archive](https://github.com/stn1slv/spec-kit-archive) | An agent merges each finished feature spec into one project spec after the merge | Bondstone checks deterministically that every finished change is reflected in the current documents; a compatibility pack may come later |
| [OpenSpec](https://github.com/Fission-AI/OpenSpec) | Keeps living specs with WHEN/THEN scenarios and merges change deltas into them on archive | A planned host rather than a rival: Bondstone adds test evidence and stages on top |
