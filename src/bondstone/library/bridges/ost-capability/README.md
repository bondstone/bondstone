---
id: BRIDGE-ost-capability
title: OST to capabilities
status: draft
name: ost-capability
kind: bridge
version: 1.0.0
provides:
- REQ-LIB-006
---

## Purpose

Hand committed discovery solutions over to the capability specs that describe them.

## Contents

- Link `realized_by` (ost:Solution → capability:Capability).
- Committed solutions must be realized; active capabilities should trace back to discovery.

## Example

```yaml
# .bondstone/profile.yaml
packs: [ost@1, capability@1]
bridges: [ost-capability@1]
```
