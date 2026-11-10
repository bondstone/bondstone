---
id: CLI-supersede
title: supersede
status: draft
synopsis: bondstone supersede ID --title TITLE [--set KEY=VALUE]... [--no-repoint]
implements:
- CAP-scaffolding
---

## Options

- `ID`: document to supersede.
- `--title TITLE`: title of the successor.
- `--set KEY=VALUE`: as for `new`.
- `--no-repoint`: keep incoming links on the old document.

## Exit codes

- `0`: success.
- `2`: configuration or usage error.

## Examples

```sh
bondstone supersede ADR-001 --title "Store habits with Drift"
```
