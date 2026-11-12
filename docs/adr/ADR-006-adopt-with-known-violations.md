---
id: ADR-006
type: adr:Decision
title: Adopt with known violations that may only shrink
status: accepted
owner: dworek
date: 2026-11-10
---

## Context

The first `check` in a repository with hundreds of existing documents can report hundreds of
errors. Fixing everything first blocks adoption, lowering severities removes the gate for new
work, and one waiver per violation buries the waivers that matter (D6 in
[the design](../design.md)).

## Decision

`bondstone baseline --known` records every current violation in `.bondstone/known.json` as a
fingerprint of rule, node and a key that names the problem, without line numbers. A matching
violation is reported as `info` and does not fail; a new one fails. Entries that no longer
match are reported until they are pruned, and with `--base` any entry added since the base is
an error, so the file can only shrink. This arrives in phase 5.

## Alternatives considered

- **One waiver per node.** Hundreds of profile entries with invented reasons and dates.
- **Fix everything before adopting.** Weeks of cleanup while new work adds more violations.

## Consequences

- A repository can adopt bondstone in one commit and gate new work from that commit on.
- The fingerprint key must be stable for every rule, which constrains how diagnostics are
  built.
- Agents are told never to create or extend the file.
