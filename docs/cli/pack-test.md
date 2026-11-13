---
id: CLI-pack-test
type: cli:Command
title: pack test
status: experimental
synopsis: bondstone pack test [--format text|json] DIR...
json_output: true
implements: [CAP-pack-tooling]
---

Runs the fixtures of packs, bridges and presets: each `fixtures/<case>/` is checked and compared with its `expected.yaml`.

## Options

- `--format text|json`: Output format (default: text).
- `DIR`: Folder of a pack, a bridge or a preset.

## Exit codes

- `0`: every fixture passed
- `1`: a fixture failed, or a component has no fixtures
- `3`: a folder holds no pack, bridge or preset

## Examples

```sh
bondstone pack test .bondstone/packs/runbooks
bondstone pack test library/src/bondstone_library/packs/*
```

## JSON output

```json
{"version": 1, "summary": {"passed": 1, "failed": 1},
 "fixtures": [{"component": "adr", "kind": "pack", "case": "valid", "path": "...", "passed": true, "problems": []}]}
```
