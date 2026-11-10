---
id: CHG-009
title: Alternative clauses (any)
status: accepted
owner: dworek
kind: feature
modifies:
- CAP-rules
- CAP-diff-checks
- CAP-profiles
---

## Why

`profile/source-change-has-proposal` requires an accepted proposal for every source or library change. The push that closes the last open proposals legitimately changes library files (README statuses) while no proposal is `accepted` any more, so the rule warned on phase 3's final push (336d0f5). The real condition is "an accepted proposal exists, or a proposal is implemented in this change", and rules cannot express "or".

## What changes

- An `any: [clause, ...]` clause that passes when at least one alternative passes, in node rules and in diff rules.
- `profile check` validates the alternatives and rejects `traced` inside `any`.
- The profile rule becomes: exists an accepted proposal, or a proposal changed to `implemented`.

## Out of scope

`all`/`not` combinators, and `traced` alternatives.
