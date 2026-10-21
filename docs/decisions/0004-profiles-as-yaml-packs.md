---
type: decision
id: ADR-0004
title: Define profiles as YAML packs over a small core
description: Profiles are made of YAML packs over a core that knows only items, types, links, owners and declared grouping; no command knows a document type, rule or pack.
status: proposed
---

# Define profiles as YAML packs over a small core

## Context and Problem Statement

An earlier design had commands tied to one pack: a `sync` command that only made sense with use cases, and a `decide` command that only made sense with separate architecture and solution building-block documents. Every new profile would then have needed new commands. Profiles also group requirements differently: simple-app in one living spec per capability, larger profiles in stories that span specs, portfolio stages or building blocks. How can profiles differ while the commands and the core stay the same?

## Considered Options

- Commands per pack
- Generic commands over pack data
- Packs as plugins with their own code
- For grouping, one "container" type that holds requirements
- For grouping, one owner per requirement plus a grouping link the profile declares

## Decision Outcome

Chosen options: "Generic commands over pack data" and, for grouping, "one owner per requirement plus a grouping link the profile declares", because loading data executes nothing and stays deterministic, and because grouping varies between profiles while ownership doesn't.

- Packs declare types, relations, stages, rules, templates and guidance in YAML. Rules are declarative, plus a small set of parameterized built-in checks. No command names a document type, rule or pack, and no pack contains code.
- Every requirement has exactly one owner, the document it is written in. The profile declares the grouping link, the work unit that `next` names, and the scope carrier whose release puts requirements in scope.
- In simple-app, a capability spec is the owner, the work unit and the scope carrier. That a requirement's prefix equals its spec's ID is a simple-app rule, not a core one.

"Container" was rejected because it merged three roles that differ in larger profiles: where a requirement is written, the unit of work, and what carries the release.

### Consequences

- Good, because a larger profile is a set of new packs; the commands, the JSON contract and the agent commands stay the same.
- Good, because loading a pack executes nothing, and the core never assumes capabilities.
- Bad, because logic that is awkward in YAML becomes a new built-in check in the engine, and a new concept needs a core change and a new pack schema version.

### Confirmation

Every command runs with zero packs active (CHECK-12), and a lint test fails if an agent command file names a type, rule or pack (SPECKIT-2).
