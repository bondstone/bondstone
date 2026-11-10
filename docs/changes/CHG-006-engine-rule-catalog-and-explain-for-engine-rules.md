---
id: CHG-006
title: Engine rule catalog and explain for engine rules
status: implemented
owner: dworek
kind: feature
modifies:
- CAP-agent-instructions
- CAP-diff-checks
delivers:
- REQ-AGT-004
---

## Why

`bondstone explain` explains pack and bridge rules, but not the engine's own rules (`bondstone/immutable`, `bondstone/link-min`, ...), which are most of what users see (engine feature 3).

## What changes

- A catalog of engine rules shipped with the package, one item per rule with when it fires, why, and how to fix it.
- `bondstone explain bondstone/<rule>` reads the catalog.
- A local `engine` pack makes the catalog a checked document: every rule is tagged where it is emitted, and a test checks that every emitted rule id is in the catalog.
- Tag ids must be complete, so text such as `bondstone: REQ-...` in a hint is not a tag (found while tagging the manifests).
- Tag regions nest: a tag inside a function no longer ends the region of the function's own tag.

## Out of scope

Translating the catalog, and links from diagnostics to a website.
