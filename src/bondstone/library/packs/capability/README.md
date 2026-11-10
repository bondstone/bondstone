---
id: PACK-capability
title: Living capability specs
status: draft
name: capability
kind: pack
version: 1.0.0
provides:
- REQ-LIB-003
---

## Purpose

Describe what the system does today, one capability per file, with requirements that code references.

## Contents

- Type `capability:Capability` in `docs/capabilities/`, with `### REQ-<CODE>-NNN: title` items (`capability:Requirement`).
- Requirements need SHALL/MUST and a `#### Scenario:`; they are code-traceable.
- Views for capabilities and requirements.

## Example

```yaml
# .bondstone/profile.yaml
packs: [capability@1]
```
