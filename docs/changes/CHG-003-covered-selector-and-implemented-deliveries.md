---
id: CHG-003
title: Covered selector and implemented deliveries
status: implemented
owner: dworek
kind: feature
modifies:
- CAP-rules
- CAP-diff-checks
delivers:
- REQ-RUL-007
- REQ-DIF-006
---

## Why

`change-capability` checks that an implemented proposal lists the requirements it delivered, but not that they are implemented. A proposal can be closed with requirements that no code implements.

## What changes

- A `covered` selector key that matches nodes tagged in code.
- `change-capability` 0.2.0: requirements delivered by an implemented proposal must be covered.
- Traced diff rules use the changed regions of a file instead of the whole file (found while implementing: any change to `cli.py` required three unrelated specs to change).

## Out of scope

Checking that the covering code changed in the same change.
