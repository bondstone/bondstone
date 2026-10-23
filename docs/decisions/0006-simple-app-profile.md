---
type: decision
id: ADR-0006
title: Make simple-app the first profile
description: Bondstone's first profile is simple-app, which replaces the earlier solo-lite design.
status: draft
---

# Make simple-app the first profile

## Context and Problem Statement

The earlier first profile, solo-lite, needed a PRD and a building-blocks document and ran five stages per feature. simple-app needs a brief, an architecture page, one living spec per capability, and decision records only for hard choices. Research on spec-driven tools showed that per-change specs drift, that heavy workflows don't pay off for small apps, and that requirement-to-test evidence is the link that proves something. The first profile also has to fit Bondstone's own repository. Which profile comes first?

## Considered Options

- solo-lite
- simple-app

## Decision Outcome

Chosen option: "simple-app", because it fits Bondstone itself and small apps, with one place for behavior and a computed backlog. It has four computed stages (frame, shape, build and release), its own rules, and components that carry both their contract (the architecture building block) and their chosen technology (the solution building block). Its documents in `docs/` form an Open Knowledge Format 0.2 bundle and use OKF's status values, so any OKF tool can read them. The PROFILE spec defines it; in 0.0 the Spec Kit extension's stopgap applies it.

### Consequences

- Good, because one place holds each capability's behavior, and the backlog is computed rather than kept by hand.
- Good, because OKF tools can read the documents without knowing Bondstone.
- Bad, because architecture and solution building blocks share one component entry; a larger profile can split them again.
- Bad, because OKF has no `proposed` or `accepted`, so decisions use `draft`, `stable` and `deprecated` instead of MADR's status words.
