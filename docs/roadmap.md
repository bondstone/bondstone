---
type: roadmap
id: ROADMAP
title: Roadmap
description: Bondstone's versions with goal, scope by capability and status, extended in place.
status: draft
---

# Roadmap

Three releases, about 27 focused days, each built with the one before. Each of the extension's four commands (`status`, `next`, `write`, `check`) keeps its name from 0.0 on; only its body moves from the bootstrap to the CLI, so nothing migrates. A capability is listed under the release that starts it; requirements that land later carry their own `Release:` line. The first version not shipped is the current one; versions are extended in place, never replaced, and shipped ones stay here with date and tag.

### V-0.0 Bootstrap
Status: active · Capabilities: SPECKIT, PROFILE · Appetite: 5 focused days

The Spec Kit extension and preset, with the four commands under their final names. A stopgap script applies the simple-app workflow (living docs, version PRDs with deltas, stories as Spec Kit specs, scoped example IDs), reads the JUnit report, and computes each requirement's status, the phase and the next step as JSON. The extension ships templates for every document, and the preset makes each spec one story with its expected and actual living-doc changes. `check`, `status` and `next` relay its output; `write` is a prompt. Approvals are made by setting `status` by hand, and manual checks by writing a `Verified:` line by hand. A pre-commit hook runs the stopgap check and rejects approvals made from an agent's shell. Each session is logged with whether `next` was right.

**No-gos:** the CLI and its PyPI package, recorded approvals, Claude Code hooks, CI.

### V-0.1 Checker
Status: planned · Capabilities: GRAPH, CHECK, EVIDENCE, SETUP · Appetite: 12 focused days

Built through the bootstrap. The extension's `check` runs `bondstone check`, and the CLI is published to PyPI. The stopgap keeps only the phase and the next step, computed from `bondstone check --json`. Includes `init`, the pre-commit hook, a CI example and the spec-gates recipe.

**No-gos:** CLI-backed `status`, `next` and `write`, `approve` and `verify`, Claude Code hooks, the release gate.

### V-0.2 Agent loop
Status: planned · Capabilities: WRITE, APPROVE, FLOW · Appetite: 10 focused days

`status`, `next` and `write` call the CLI, and the stopgap script is deleted. `approve` and `verify` record approvals and manual checks with an actor, time and hash, and refuse to run from an agent's shell. Adds profile phases, Claude Code hooks and the release gate; 0.2 gates its own release.

**No-gos:** team features, native Windows, impact reports, an MCP server.

## Later

Not scheduled. Profiles, packs, templates and hosts arrive without new commands; only the features in the last line may add one.

- **Users:** small teams sharing one repository and one set of rules; later, organizations that need portfolio, architecture and change governance on the same documents.
- **Profiles:** team and enterprise, including stories, sprints, portfolio phases and separate building-block items.
- **Packs:** release, mobile store, use cases, and compatibility with the consolidated spec written by spec-kit-archive.
- **Hosts:** BMAD and OpenSpec.
- **Features:** an impact report, native Windows support, an MCP server.

