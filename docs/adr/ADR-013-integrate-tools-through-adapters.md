---
id: ADR-013
type: adr:Decision
title: Integrate other tools through adapters, Spec Kit first
status: accepted
owner: dworek
date: 2026-11-10
---

## Context

Spec Kit and BMAD produce artifacts that should obey the repository's rules, and their
templates should not contradict those rules. Both tools change their customization mechanisms
between releases (D13 in [the design](../design.md)).

## Decision

Each tool gets an adapter: a pack that types the tool's artifacts by path, a bridge that
connects them to the living documents, and generated templates. The Spec Kit pack and bridges
are part of the MVP in phase 4, in the place of the POC's `change` pack. Spec Kit template
generation and the BMAD adapter follow in phase 6. Each adapter declares the tool versions it
was tested with and refuses to install on others.

## Alternatives considered

- **The POC's own `change` pack first, Spec Kit later.** It would repeat what Spec Kit does
  better and delay the integration that goal G5 asks for.
- **Adapters in separate repositories.** Their rules and templates could drift from the
  packs they depend on.

## Consequences

- A Spec Kit feature is the per-change record in the MVP, and its status is derived from its
  files.
- Every new tool release is a compatibility question that the adapter's pinned versions make
  explicit.
