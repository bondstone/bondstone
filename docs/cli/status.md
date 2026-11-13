---
id: CLI-status
type: cli:Command
title: status
status: stable
synopsis: bondstone status [--format text|json] ID STATUS
json_output: true
implements: [CAP-scaffolding]
---

Changes the status of a document or an item, when its lifecycle allows the step.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `ID`: See the description above.
- `STATUS`: See the description above.

## Exit codes

- `0`: done
- `1`: refused; nothing was changed
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone status ADR-004 accepted
bondstone status REQ-REM-003 active
```

## JSON output

```json
{"version": 1, "id": "ADR-004", "path": "docs/adr/ADR-004-use-sqlite.md", "old": "proposed", "new": "accepted",
 "changed": true, "views": ["docs/generated/decisions.md"]}
```
