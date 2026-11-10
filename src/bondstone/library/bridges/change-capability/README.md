---
id: BRIDGE-change-capability
title: Proposals update living specs
status: active
name: change-capability
kind: bridge
version: 0.2.0
provides:
- REQ-LIB-006
---

## Purpose

Make sure a proposal is closed only when the capability specs contain what it delivered, and the code implements it.

## Contents

- Links `modifies` (→ capability:Capability) and `delivers` (→ capability:Requirement).
- Implemented features must deliver requirements that are tagged in code (`covered`).
- Roles `change` and `living-spec`.

## Example

```yaml
# .bondstone/profile.yaml
packs: [change@0.1, capability@1]
bridges: [change-capability@0.2]
```
