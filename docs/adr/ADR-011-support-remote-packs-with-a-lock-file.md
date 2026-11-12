---
id: ADR-011
type: adr:Decision
title: Support remote packs with a lock file in v1
status: accepted
owner: Adam Dworzyński
date: 2026-11-10
---

## Context

Packs are meant to be shared between repositories. Copying them into each repository's
`.bondstone/packs` works for one team and drifts for many (D11 in
[the design](../design.md)).

## Decision

In v1, phase 5, a profile may name git sources, written `host/org/repo//path@ref`.
`.bondstone/bondstone.lock` records the resolved commit and a SHA-256 of the files of every
non-local component. `check` uses only the lock and a local cache, and `bondstone update`
refreshes both.

## Alternatives considered

- **Local packs and installed library packages only**, until a second repository needs
  sharing. Less to build, but presets (ADR-004) are of little use without a way to fetch them.

## Consequences

- `check` never touches the network, so the gate stays deterministic.
- Until phase 5 the resolver reads the profile's `sources` folders only.
