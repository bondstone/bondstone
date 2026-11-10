---
id: ADR-008
type: adr:Decision
title: Declare ids and paths with one template each
status: accepted
owner: dworek
date: 2026-11-10
---

## Context

A POC type declared its ids and location with five keys: `id_format`, `id_pattern`, `paths`,
`dir` and `filename`. Scaffolding read some of them and validation read others, so they could
disagree (D8 in [the design](../design.md)).

## Decision

A type has one `id` template, such as `ADR-{n:03d}`, and one `path` template, such as
`docs/adr/{id}-{slug}.md`. The engine derives the id pattern (`^ADR-\d{3,}$`) and the glob
that finds the type's documents (`docs/adr/*.md`) from them. `id_pattern` remains only as an
explicit override of the derived pattern.

## Alternatives considered

- **The POC's five keys.** Flexible, but two sources for the same fact.

## Consequences

- Scaffolding and validation read the same template, so a scaffolded document always passes
  the id and path checks.
- An item's id template may use a field of its document, such as `REQ-{code}-{n:03d}`; the
  item must then carry its own document's value.
- Layouts that a template cannot express need a new placeholder in the engine.
