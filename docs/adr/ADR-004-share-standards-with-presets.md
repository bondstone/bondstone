---
id: ADR-004
type: adr:Decision
title: Share standards across repositories with presets
status: accepted
owner: dworek
date: 2026-11-10
---

## Context

An organisation wants the same packs, bridges and a few rules that cannot be loosened in all
of its repositories. Without a mechanism for that, profiles are copied and drift apart (D4 in
[the design](../design.md)).

## Decision

A preset is a partial profile kept in git. A profile names presets under `extends`, and a
preset may mark rules as `locked`, so that a profile can raise their severity but not lower
it or waive them. Severities apply in the order rule default, presets in `extends` order,
then the profile. Presets arrive in phase 4.

## Alternatives considered

- **Named profiles inside packs** (the design sketch). A pack would then have to know which
  other packs it is combined with, which principle 2 forbids.
- **Copying profiles between repositories.** Nothing detects that the copies have diverged.

## Consequences

- `locked` already exists on rules, and the profile format reserves `extends`. Until phase 4
  a profile that names a preset is a configuration error.
- Presets need the remote sources and the lock file of ADR-011 to be shared between
  repositories without copying.
