---
type: decision
id: ADR-0004
title: Define profiles as YAML packs over a small core
description: A profile is a set of YAML packs over a core that knows only items, types, links, owners and declared grouping; larger profiles add packs, never commands.
status: proposed
---

# Define profiles as YAML packs over a small core

## Context and Problem Statement

The simple-app profile groups requirements into one living spec per capability. Team and enterprise profiles will group them differently: stories that span specs, portfolio stages, building-block items. How does the core stay the same while profiles differ, and how does a profile say how requirements are grouped?

## Considered Options

- A fixed set of documents and rules built into the code
- Profiles as YAML packs over a small core
- Profiles as Python plugins
- For grouping: one "container" type that holds requirements
- For grouping: one owner per requirement, plus a grouping link the profile declares

## Decision Outcome

Chosen option: "Profiles as YAML packs over a small core", with "one owner per requirement, plus a grouping link the profile declares", because data can be validated and stays deterministic, and because grouping varies between profiles while ownership does not.

- The core knows items, types, links, owners, grouping, scope, evidence, approvals and the active change.
- Every requirement has exactly one owner, the document it is written in.
- The profile declares the grouping link, the work unit `next` names, and the scope carrier whose release puts requirements in scope.
- Packs add types, rules, stages and templates, never commands.
- In simple-app, the owner, work unit and scope carrier are all the living spec. That a requirement's prefix equals its spec's ID is a simple-app rule, not a core one.

### Consequences

- Good, because a team profile with stories adds packs, not commands or core code.
- Good, because the core never assumes capabilities; stage criteria count work units.
- Bad, because a pack can only describe what the core supports; a new concept means a core change and a new pack schema version.
- Bad, because packs need a versioned schema (`bondstone: 1`) and strict YAML loading.
- Rejected "container", because it merged three roles (where a requirement is written, the unit of work, and what carries the release) that differ in larger profiles.
