---
id: CLI-new
type: cli:Command
title: new
status: experimental
synopsis: bondstone new [--format text|json] --title TITLE [--set KEY=VALUE] TYPE
json_output: true
implements: [CAP-scaffolding]
---

Creates a document of a type with the next free id, at the type's path, from the type's template.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `--title TITLE`: Title of the new document.
- `--set KEY=VALUE`: A frontmatter field or link of the new document; may be repeated.
- `TYPE`: A document type such as adr:Decision.

## Exit codes

- `0`: done
- `1`: refused; nothing was changed
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone new adr:Decision --title "Use SQLite"
bondstone new capability:Capability --title "Reminders" --set code=REM
```

## JSON output

```json
{"version": 1, "id": "ADR-004", "path": "docs/adr/ADR-004-use-sqlite.md", "views": ["docs/generated/decisions.md"]}
```
