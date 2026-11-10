---
id: CLI-profile-check
title: profile check
status: draft
synopsis: bondstone profile check [--format text|json]
implements:
- CAP-profiles
json_output: true
---

## Options

- `--format text|json`: output format.

## Exit codes

- `0`: the profile is valid.
- `1`: the check failed.
- `2`: configuration error, e.g. no profile found.

## Examples

```sh
bondstone profile check
```

## JSON output

```json
{
  "diagnostics": [
    {"rule": "bondstone/link-broken", "severity": "error", "message": "...",
     "path": "docs/x.md", "line": 5, "node": "SOL-2", "hint": "..."}
  ],
  "summary": {"errors": 1, "warnings": 0}
}
```

Same shape as `check`, without `nodes`.
