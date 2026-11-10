---
id: BRIDGE-release-change
title: Releases include proposals
status: active
name: release-change
kind: bridge
version: 0.1.0
provides:
- REQ-LIB-006
---

## Purpose

Build the changelog from the proposals each release includes.

## Contents

- Link `includes` (release:Release → change:Proposal).
- Releases include only implemented proposals; implemented proposals should be released.

## Example

```yaml
# .bondstone/profile.yaml
packs: [release@0.1, change@0.1]
bridges: [release-change@0.1]
```
