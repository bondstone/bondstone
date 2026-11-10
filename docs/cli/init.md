---
id: CLI-init
title: init
status: draft
synopsis: bondstone init [--packs LIST] [--bridges LIST]
implements:
- CAP-scaffolding
---

## Options

- `--packs LIST`: comma-separated pack references, e.g. `adr@1,ost@1`.
- `--bridges LIST`: comma-separated bridge references.

## Exit codes

- `0`: profile created and valid.
- `1`: the profile has errors (printed).
- `2`: a profile already exists.

## Examples

```sh
bondstone init --packs adr@1,capability@1 --bridges adr-capability@1
```
