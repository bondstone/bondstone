---
id: CLI-baseline
title: baseline
status: experimental
synopsis: bondstone baseline [REF]
implements:
- CAP-diff-checks
---

## Options

- `REF`: git ref to record (default `HEAD`).

## Exit codes

- `0`: success.
- `2`: configuration or usage error.

## Examples

```sh
bondstone baseline
bondstone baseline v0.1.0
```
