---
id: CLI-check
title: check
status: stable
synopsis: bondstone check [--base REF] [--format text|json] [--fail-on error|warn]
implements:
- CAP-rules
- CAP-graph
- CAP-diff-checks
- CAP-code-traceability
- CAP-views
- CAP-agent-instructions
json_output: true
---

## Options

- `--base REF`: also run diff checks against the git ref (status transitions, immutability, creation status, baseline, `on_change` rules).
- `--format text|json`: output format (default `text`).
- `--fail-on error|warn`: lowest severity that fails the check (default `error`).

## Exit codes

- `0`: no errors (and no warnings with `--fail-on warn`).
- `1`: the check failed.
- `2`: configuration error, e.g. no profile found.

## Examples

```sh
bondstone check
bondstone check --base origin/main --format json
```

## JSON output

```json
{
  "diagnostics": [
    {"rule": "bondstone/link-broken", "severity": "error", "message": "...",
     "path": "docs/x.md", "line": 5, "node": "SOL-2", "hint": "..."}
  ],
  "summary": {"errors": 1, "warnings": 0, "nodes": 15}
}
```

`path`, `line`, `node` and `hint` are omitted when unknown.
