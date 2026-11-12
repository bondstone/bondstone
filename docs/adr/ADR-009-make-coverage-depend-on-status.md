---
id: ADR-009
type: adr:Decision
title: Make code coverage depend on status
status: accepted
owner: Adam Dworzyński
date: 2026-11-10
---

## Context

In the POC, `code-traceable: {coverage: warn}` applied to every node of a type. A spec written
before its code, which is what Spec Kit encourages, immediately reported requirements that are
"not referenced from code". Teams then switched coverage off for the whole type or wrote
requirements after the code (D9 in [the design](../design.md)).

## Decision

`code-traceable.when` lists the statuses that need code; nodes in other statuses are not
reported as uncovered. `code-traceable.retired` lists the statuses that must not have code: a
tag on such a node is `bondstone/tag-retired` (warn). Items get a status of their own from an
optional `Status:` line under their heading, and take the lifecycle's `default` status
without it. A `covered` clause and selector make the same question available to named rules.

## Alternatives considered

- **Coverage per type only, as in the POC.** Simple, but it punishes spec-first work.

## Consequences

- A planned requirement needs no code, an active one does, and a tag left on a removed one
  warns.
- The default status should be the strict one, so forgetting the `Status:` line never weakens
  the check.
- Lifecycle rules apply to items too: with `--base`, a requirement moving from `active` back
  to `planned` must be a transition the lifecycle allows.
