---
id: ADR-014
type: adr:Decision
title: Leave portfolio and cross-repository links until after v1
status: accepted
owner: Adam Dworzyński
date: 2026-11-10
---

## Context

Organisations want to see documents across repositories: which services implement a
capability, which decisions apply everywhere. That needs links between repositories and an
aggregated view (D14 in [the design](../design.md)).

## Decision

Cross-repository links (`repo:ID`) and portfolio aggregation come after v1. v1 provides their
foundation: `bondstone graph` exports the graph of one repository in a documented format.

## Alternatives considered

- **In v1, by aggregating `graph` exports in a portfolio repository.** Possible, but it would
  fix an export format and a link syntax before one repository's model has settled.

## Consequences

- In v1 every id is local to its repository and every link resolves inside it.
- A portal or a portfolio check can be built on `bondstone graph` without changes to the
  engine.
