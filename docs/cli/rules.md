---
id: CLI-rules
title: rules
status: draft
synopsis: bondstone rules [--format text|json]
implements:
- CAP-agent-instructions
json_output: true
---

## Options

- `--format text|json`: output format.

## Exit codes

- `0`: success.
- `2`: configuration or usage error.

## Examples

```sh
bondstone rules --format json
```

## JSON output

```json
[{"id": "adr/alternatives-considered", "owner": "adr", "severity": "warn",
  "locked": false, "description": "...", "spec": {}}]
```

`severity` is the effective severity after profile overrides.
