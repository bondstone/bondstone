---
id: CLI-explain
type: cli:Command
title: explain
status: stable
synopsis: bondstone explain [--format text|json] RULE
json_output: true
implements: [CAP-agent-guidance]
---

Explains one rule: what it asks, why, how to satisfy it, and where its severity comes from.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `RULE`: A rule id such as adr/alternatives-considered.

## Exit codes

- `0`: done
- `1`: unknown rule; close matches are suggested
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone explain adr/alternatives-considered
bondstone explain bondstone/immutable --format json
```

## JSON output

The entry of `bondstone rules --format json` for that rule, with `version`; a declared rule adds `spec`, and `asks` when it is a diff rule; an engine rule has `fires`, `why` and `fix` in place of `description`.
