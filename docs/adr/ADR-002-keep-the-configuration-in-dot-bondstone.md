---
id: ADR-002
type: adr:Decision
title: Keep the configuration in .bondstone/profile.yaml
status: accepted
owner: Adam Dworzyński
date: 2026-11-10
---

## Context

A repository's bondstone setup is more than one file: the profile, local packs and bridges,
later a lock file and the list of known violations. The question was where the profile lives
(D2 in [the design](../design.md)).

## Decision

The profile is `.bondstone/profile.yaml`. Local packs and bridges live next to it in
`.bondstone/packs/`, and the lock file and `known.json` will join them. Bondstone finds the
repository root by looking for that file in the current folder and its parents.

## Alternatives considered

- **`bondstone.yaml` in the repository root.** More visible, but the packs, the lock file and
  the known violations would still need a folder, so the setup would be split over two places.

## Consequences

- Everything bondstone reads as configuration is in one folder, which is easy to review and to
  protect with code-owner rules.
- The folder is hidden by default in file listings, so the README of a repository should
  mention it.
