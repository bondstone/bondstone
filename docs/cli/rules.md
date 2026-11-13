---
id: CLI-rules
type: cli:Command
title: rules
status: stable
synopsis: bondstone rules [--format text|json]
json_output: true
implements: [CAP-agent-guidance]
---

Lists every rule that can report in this repository with the severity `check` applies, and says when a preset or the profile changed it.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).

## Exit codes

- `0`: done
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone rules
bondstone rules --format json
```

## JSON output

```json
{"version": 1, "rules": [{"id": "adr/alternatives-considered", "kind": "node", "severity": "error",
                           "default": "warn", "set_by": "profile", "locked": false,
                           "description": "...", "declared_in": ".bondstone/packs/adr/pack.yaml"}]}
```
