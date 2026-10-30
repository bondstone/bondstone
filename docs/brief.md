---
type: brief
id: BRIEF
title: Bondstone
description: A deterministic CLI, with a Spec Kit extension and preset, that says which approved requirements are proven by passing tests, and what to do next.
status: draft
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

Terms are defined in the [glossary](glossary.md).

## Goals

**In 90 days**

- Release 0.2 with Bondstone's own repository passing its release gate.
- Give every requirement its evidence status.
- Compute the project's phase and one next step on every run, identically in every session, from release 0.0.
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
- Phases are computed, never stored; only approvals and `Verified:` lines are stored.
- Approved behavior lives in current documents with stable requirement IDs; a change isn't finished until those documents reflect it.
- A profile is a set of YAML packs; larger profiles add packs, never commands.
- The core stays host-agnostic; Spec Kit is the first host, kept outside the core.

## Releases

Releases are planned in the [roadmap](roadmap.md): 0.0 bootstrap, 0.1 checker, 0.2 agent loop, about 27 focused days in all, each built with the one before.

## Risks

- **Agents don't follow the flow.** This is the riskiest assumption, and 0.0 exists to test it. The session log records whether the agent started from `next`, stayed on its step, named tests after IDs and filled in `## Living doc changes`. If it follows the step unprompted in fewer than 8 of 10 sessions, the flow is rethought before 0.2.
- **Empty tests.** An agent can name a test after a requirement and assert nothing. Console examples run as tests, and the person reviews test names; Bondstone does not judge test quality.
- **Spec Kit moves fast.** Version 0.10 removed `init` flags, and Claude now installs its commands as skills. The extension pins the Spec Kit versions it supports, and CI runs an install smoke test.
- **Appetite.** 0.0 holds 19 requirements in 5 days, and 0.1 about 50 in 12. If 0.1 runs out of time, the spec-gates recipe goes first, then the CI example.

## Alternatives

| Tool | What it does | How Bondstone differs |
| --- | --- | --- |
| [DocGuard](https://github.com/raccioly/docguard) | A Node.js CLI and Spec Kit extension with 34 validators, starter to enterprise profiles, a living-spec registry and an MCP server; it links requirement IDs to test declarations in test files | Pass or fail per requirement from test results, not mentions; person-only, hash-pinned approvals; one computed next step |
| [SpecAssay](https://github.com/rdryfoos/specassay) | A deterministic Spec Kit gate that finds acceptance-criterion IDs in test names | Reads whether those tests passed, and computes a phase and next step |
| [spec-validate](https://github.com/aeltayeb/spec-kit-spec-validate) | A Spec Kit extension that gates reviews and keeps hook-enforced approval state with a SHA-256 hash | Overlaps on approvals; Bondstone ties them to test evidence and phases |
| [spec-gates](https://github.com/schwichtgit/spec-gates) | Runs one quality gate identically at Claude Code hooks, git hooks and CI; also runs acceptance checks and requires approval trailers on protected files | Complementary, with some overlap on approvals: Bondstone can run as one of its gates |
| [spec-kit-archive](https://github.com/stn1slv/spec-kit-archive) | An agent merges each finished feature spec into one project spec after the merge | Bondstone checks deterministically that every finished change is reflected in the current documents; a compatibility pack may come later |
| [OpenSpec](https://github.com/Fission-AI/OpenSpec) | Keeps living specs with WHEN/THEN scenarios and merges change deltas into them on archive | A planned host rather than a rival: Bondstone adds test evidence and phases on top |
