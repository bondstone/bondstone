---
id: ADR-005
type: adr:Decision
title: Exempt a change from a diff rule with a commit trailer
status: accepted
owner: dworek
date: 2026-11-10
---

## Context

A traced diff rule fires on any edit inside a tagged code region, and many edits change no
behaviour: a rename, a move, a dependency bump, a reformat. Without an exemption the author
either edits the spec for nothing, which hides the real updates, or weakens the profile for
every future change (D5 in [the design](../design.md)).

## Decision

A diff rule may declare `exempt: {trailer: <name>}`. A commit in the checked range then
exempts the change with a trailer such as `Spec-Impact: none (pure move)`. The value must be
`none (<reason>)` with a reason; `none [CAP-reminders] (<reason>)` limits it to the listed
nodes. An exempted violation is still reported, as `bondstone/exemption-used` (info) with the
commit and the reason, and a malformed trailer is `bondstone/exemption-invalid` (error).
`check --no-exemptions` ignores every trailer.

## Alternatives considered

- **Waivers only.** A waiver is permanent and per node; reviewers see a policy change where
  an explanation for one change was meant.
- **A pull request label.** It needs the forge's API, so results differ locally and in CI, and
  the label is not in git history.
- **An ignore comment in code.** It pollutes the code and outlives the change.
- **Trivial spec edits.** This is the noise the mechanism exists to avoid.

## Consequences

- The exemption sits in history next to the change and is visible in review. `check` reads it
  with `git log`, so it stays offline and deterministic.
- A squash merge keeps a trailer only if the squashed message keeps it. Pull request CI checks
  the branch commits, so the gate still sees it.
- Use can be counted per rule and per author once `bondstone report` exists.
