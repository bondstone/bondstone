---
id: CLI-profile-check
type: cli:Command
title: profile check
status: experimental
synopsis: bondstone profile check [--format text|json]
json_output: true
implements: [CAP-profiles]
---

Validates the profile and the presets, packs and bridges it uses, without reading any document.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).

## Exit codes

- `0`: the configuration is valid; warnings may be listed
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone profile check
bondstone profile check --format json
```

## JSON output

```json
{"version": 1, "summary": {"errors": 1, "warnings": 0, "info": 0, "nodes": 15},
 "diagnostics": [{"rule": "bondstone/link-broken", "severity": "error", "path": "docs/x.md", "line": 5,
                  "node": "CAP-a", "message": "...", "hint": "..."}]}
```

`path`, `line`, `node`, `hint`, `fix` and `exempted_by` are left out when they do not apply.
