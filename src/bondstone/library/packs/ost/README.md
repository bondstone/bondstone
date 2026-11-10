---
id: PACK-ost
title: Opportunity Solution Tree
status: active
name: ost
kind: pack
version: 1.0.0
provides:
- REQ-LIB-002
---

## Purpose

Continuous product discovery: outcomes, the opportunities that serve them, solutions and the experiments that test them.

## Contents

- Types `ost:Outcome`, `ost:Opportunity`, `ost:Solution`, `ost:Experiment` in `docs/discovery/`.
- Links `serves`, `addresses`, `tests`; rules on evidence and results.
- View `docs/generated/opportunity-solution-tree.md`.

## Example

```yaml
# .bondstone/profile.yaml
packs: [ost@1]
```
