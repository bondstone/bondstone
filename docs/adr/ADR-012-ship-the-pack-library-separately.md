---
id: ADR-012
type: adr:Decision
title: Ship the pack library as a separate optional package
status: accepted
owner: dworek
date: 2026-11-10
---

## Context

The POC bundled its packs inside the engine. That made the engine release whenever a pack
changed and suggested that the bundled methods were part of bondstone itself, against
principle 1: the engine knows no methodology (D12 in [the design](../design.md)).

## Decision

The engine ships no packs. The library is a separate optional package, `bondstone-library`,
in the same repository, versioned on its own and registered through a Python entry point. The
resolver treats it like any other source, and nothing loads unless a profile names it.

## Alternatives considered

- **Bundled inside the engine, as in the POC.** One install, but engine and packs are
  versioned together.
- **A separate repository.** Clean separation, but engine and library changes that belong
  together could not be made in one pull request.

## Consequences

- `pip install bondstone` installs the engine alone, and a profile with only local packs is a
  complete setup.
- The library uses no extension point that a user's own packs cannot use.
- Until the library package exists (phase 4), this repository takes `adr`, `capability` and
  their bridge from the example's pack folder.
