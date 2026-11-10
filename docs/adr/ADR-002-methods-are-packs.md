---
id: ADR-002
title: The engine knows no methodology; methods are packs
status: accepted
owner: dworek
date: '2026-11-10'
---

## Context

Teams use different methods (ADRs, Opportunity Solution Trees, TOGAF-like architecture, portfolio management) and combine them differently per project.

## Decision

The engine only loads typed documents into a graph and evaluates declarative rules. Every method is a versioned pack that defines types, fields, sections, links, lifecycles, rules, views, templates and agent guidance.

## Alternatives considered

- A fixed built-in model (like most spec-driven tools): simple, but fits one way of working.
- Plugins written in code: flexible, but rules stop being reviewable data.

## Consequences

New methods need no engine changes. The rule language must be expressive enough; gaps become engine features rather than pack-specific code.
