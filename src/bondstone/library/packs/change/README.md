---
id: PACK-change
title: Change proposals
status: draft
name: change
kind: pack
version: 0.1.0
provides:
- REQ-LIB-004
---

## Purpose

Review changes before they are made, and close them only when the living documentation reflects them.

## Contents

- Type `change:Proposal` in `docs/changes/` (`CHG-NNN`), statuses draft → accepted → implemented (or rejected/withdrawn).
- `kind`: feature, fix, refactor, docs or breaking; breaking changes need a `Migration` section.
- Views of open and implemented proposals.

## Example

```yaml
# .bondstone/profile.yaml
packs: [change@0.1]
```
