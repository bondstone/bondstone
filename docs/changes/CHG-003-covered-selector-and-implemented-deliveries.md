---
id: CHG-003
title: Covered selector and implemented deliveries
status: draft
owner: dworek
kind: feature
modifies:
- CAP-rules
---

## Why

`change-capability` checks that an implemented proposal lists the requirements it delivered, but not that they are implemented. A proposal can be closed with requirements that no code implements.

## What changes

- A `covered` selector key that matches nodes tagged in code.
- `change-capability` 0.2.0: requirements delivered by an implemented proposal must be covered.

## Out of scope

Checking that the covering code changed in the same change.
