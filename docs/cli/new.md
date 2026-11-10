---
id: CLI-new
title: new
status: draft
synopsis: bondstone new TYPE --title TITLE [--set KEY=VALUE]...
implements:
- CAP-scaffolding
---

## Options

- `TYPE`: qualified (`adr:Decision`) or unqualified (`Decision`) type name.
- `--title TITLE`: required.
- `--set KEY=VALUE`: frontmatter value, parsed as YAML when possible; repeatable. `--set id=...` overrides the id.

## Exit codes

- `0`: success.
- `2`: configuration or usage error.

## Examples

```sh
bondstone new adr:Decision --title "Use SQLite"
bondstone new release:Release --title "Lock files" --set version=0.2.0
```
