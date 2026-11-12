---
id: CLI-supersede
type: cli:Command
title: supersede
status: experimental
synopsis: bondstone supersede [--format text|json] --title TITLE [--set KEY=VALUE] ID
json_output: true
implements: [CAP-scaffolding]
---

Replaces a document that may no longer be edited: creates the successor, marks the old one `superseded` and moves the links to the new one.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `--title TITLE`: Title of the new document.
- `--set KEY=VALUE`: A frontmatter field or link of the new document; may be repeated.
- `ID`: The document to replace.

## Exit codes

- `0`: done
- `1`: refused; nothing was changed
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone supersede ADR-002 --title "Use PostgreSQL"
```

## JSON output

```json
{"version": 1, "id": "ADR-005", "path": "docs/adr/ADR-005-use-postgresql.md",
 "updated": ["docs/capabilities/storage.md: constrained_by ADR-002 -> ADR-005"], "skipped": [], "views": []}
```
