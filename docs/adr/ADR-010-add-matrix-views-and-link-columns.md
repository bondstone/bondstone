---
id: ADR-010
type: adr:Decision
title: Add matrix views and link columns in v1
status: accepted
owner: Adam Dworzyński
date: 2026-11-10
---

## Context

Table and tree views cover indexes and traceability chains. Two things they cannot show came
up repeatedly: which rows relate to which columns (requirements against features), and the
linked documents of a node inside a table cell (D10 in [the design](../design.md)).

## Decision

v1 gets a `matrix` layout with `rows`, `cols` and `via` links, and table columns that name an
outgoing link (`realizes`) or an incoming one (`<-satisfies`) and render as linked ids. Both
arrive in phase 4.

## Alternatives considered

- **Defer both.** Tree views already show traceability, but a matrix is what people ask for
  when they review coverage.

## Consequences

- The view renderers keep a common contract: a view is rendered from the graph alone, so
  `check` can tell that a committed view is stale.
- Until phase 4, a view's `render` is `table` or `tree`.
