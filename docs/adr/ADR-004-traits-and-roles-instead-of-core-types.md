---
id: ADR-004
title: Traits and roles instead of shared core types
status: accepted
owner: dworek
date: '2026-11-10'
---

## Context

Generic rules ("every change updates a living spec") need to work across packs, but forcing every method into a shared ontology bends the methods and couples every pack to one model.

## Decision

The engine defines mechanical traits (lifecycle, owned, supersedable, immutable, code-traceable, indexed) that types opt into. Meaning comes from roles, which only bridges and profiles assign to types.

## Alternatives considered

- Abstract core types that packs specialise: reusable rules, but endless arguments about the model.
- No generic rules at all: every combination re-implements the same checks.

## Consequences

Packs carry no shared concepts. Generic rules and views select by trait or role. Profiles or bridges have to assign roles.
