---
id: PACK-release
title: Releases and changelog
status: active
name: release
kind: pack
version: 0.1.0
provides:
- REQ-LIB-005
---

## Purpose

Plan and publish versions, and generate the changelog from them.

## Contents

- Type `release:Release` in `docs/releases/` (`vX.Y.Z`, created with `--set version=X.Y.Z`), planned → released.
- Generated `CHANGELOG.md`.

## Example

```yaml
# .bondstone/profile.yaml
packs: [release@0.1]
```
