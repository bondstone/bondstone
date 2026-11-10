---
id: PACK-adr
title: Architecture Decision Records
status: draft
name: adr
kind: pack
version: 1.0.0
provides:
- REQ-LIB-001
---

## Purpose

Record architecturally significant decisions with their context, alternatives and consequences.

## Contents

- Type `adr:Decision` in `docs/adr/` (`ADR-NNN`), statuses proposed → accepted/rejected → deprecated/superseded.
- Accepted decisions are immutable; replace them with `bondstone supersede`.
- Rule `alternatives-considered` (warn); view `docs/generated/decisions.md`.

## Example

```yaml
# .bondstone/profile.yaml
packs: [adr@1]
```
