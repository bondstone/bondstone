---
id: BRIDGE-change-adr
title: Proposals rely on decisions
status: active
name: change-adr
kind: bridge
version: 0.1.0
provides:
- REQ-LIB-006
---

## Purpose

Link proposals to the decisions they depend on.

## Contents

- Link `decided_by` (change:Proposal → adr:Decision).
- A proposal is implemented only on accepted decisions.

## Example

```yaml
# .bondstone/profile.yaml
packs: [change@0.1, adr@1]
bridges: [change-adr@0.1]
```
