---
type: decision
id: ADR-0005
title: Keep one living spec per capability, changed in the same commit
description: In simple-app, behavior is specified once per capability and updated together with the tests and code that change it.
status: draft
---

# Keep one living spec per capability, changed in the same commit

## Context and Problem Statement

Spec Kit writes one spec per change, which describes that change rather than the system and goes stale once the change ships. Without a living spec, neither people nor agents can tell what the app is supposed to do now. This is a simple-app decision: the core only requires that approved behavior lives in current documents with stable requirement IDs, as the brief's principles say.

## Considered Options

- Spec Kit's per-change specs only
- OpenSpec-style deltas, merged into living specs when a change is archived
- An agent merges finished specs into one project spec after each merge
- One living spec per capability, changed in the same commit as its tests and code

## Decision Outcome

Chosen option: "One living spec per capability, changed in the same commit as its tests and code", because behavior, its tests and its code then stay in one commit, and every step can be checked deterministically at commit time and in CI. A Spec Kit change lists the requirement IDs it implements, adds, changes or removes under `## Spec changes`, and `change-reflected` checks that a finished change is reflected in the specs. The backlog is computed as the in-scope requirements without passing evidence.

### Consequences

- Good, because there is no merge step after the fact, and no agent run that CI can't repeat.
- Good, because for a CLI the living spec doubles as the reference documentation, and its console examples run as tests.
- Bad, because the Bondstone preset changes Spec Kit's spec template by appending a `## Spec changes` section.
- Bad, because during a change, the Spec Kit spec's own `FR-` requirements duplicate the living spec; they are working notes for that change.
- Later, a compatibility pack can treat the consolidated spec that spec-kit-archive writes as the living spec, for projects that prefer an agent merge.
