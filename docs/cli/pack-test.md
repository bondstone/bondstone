---
id: CLI-pack-test
title: pack test
status: draft
synopsis: bondstone pack test DIR...
implements:
- CAP-pack-testing
---

## Options

- `DIR...`: pack or bridge directories, each with a `fixtures/` folder.

## Exit codes

- `0`: every case passed.
- `1`: a case failed.
- `2`: a directory has no fixtures.

## Examples

```sh
bondstone pack test src/bondstone/library/packs/* .bondstone/packs/*
```
