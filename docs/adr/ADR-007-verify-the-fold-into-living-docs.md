---
id: ADR-007
type: adr:Decision
title: Verify that changes are folded into living docs, do not merge them
status: accepted
owner: Adam Dworzyński
date: 2026-11-10
---

## Context

Per-change records such as a Spec Kit feature describe a delta. Somebody has to fold that
delta into the living documents, or they go stale. OpenSpec does it with delta files that an
`archive` command merges (D7 in [the design](../design.md)).

## Decision

In v1 bondstone only verifies the fold. Links such as `delivers` from a feature to the
requirements it implements, and rules over those links, fail the gate until the living
documents were updated by a person or an agent. Bondstone does not merge deltas itself.

## Alternatives considered

- **OpenSpec-style delta files merged by an `archive` command.** It automates the fold, but
  needs a delta format for every document type and makes bondstone a workflow engine, which
  is a non-goal.

## Consequences

- The engine stays a checker: it reads documents and never rewrites their content.
- The quality of the fold depends on the author; the rules can only see that the living
  document changed and is linked.
