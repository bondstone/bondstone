---
type: decision
id: ADR-0009
title: Make simple-app the first profile
description: Bondstone's first profile is simple-app, which replaces the earlier solo-lite design.
status: proposed
---

# Make simple-app the first profile

## Context and Problem Statement

The earlier first profile, solo-lite, needed a PRD and a building-blocks document and ran five stages per feature. simple-app needs a brief, an architecture page, one living spec per capability, and decision records only for hard choices. Research on spec-driven tools showed that per-change specs drift, that heavy workflows don't pay off for small apps, and that requirement-to-test evidence is the link that proves something. The first profile also has to fit Bondstone's own repository. Which profile comes first?

## Considered Options

- solo-lite
- simple-app

## Decision Outcome

Chosen option: "simple-app", because it fits Bondstone itself and small apps, with one place for behavior and a computed backlog. It has four computed stages (frame, shape, build and release), ten rules, and components that carry both their contract (the architecture building block) and their chosen technology (the solution building block). The PROFILE spec defines it.

### Consequences

- Good, because one place holds each capability's behavior, and the backlog is computed rather than kept by hand.
- Bad, because architecture and solution building blocks share one component entry; a larger profile can split them again.
