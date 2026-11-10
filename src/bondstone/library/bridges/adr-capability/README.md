---
id: BRIDGE-adr-capability
title: Decisions constrain capabilities
status: draft
name: adr-capability
kind: bridge
version: 1.0.0
provides:
- REQ-LIB-006
---

## Purpose

Connect capability specs to the decisions they must respect.

## Contents

- Link `constrained_by` (capability:Capability → adr:Decision).
- Only live decisions may constrain; accepted decisions should constrain something.

## Example

```yaml
# .bondstone/profile.yaml
packs: [adr@1, capability@1]
bridges: [adr-capability@1]
```
