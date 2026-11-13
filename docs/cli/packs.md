---
id: CLI-packs
type: cli:Command
title: packs
status: stable
synopsis: bondstone packs [--format text|json]
json_output: true
implements: [CAP-pack-tooling]
---

Lists the packs, bridges and presets in the profile's sources and in installed packages, and marks the ones the profile uses. Works without a profile.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).

## Exit codes

- `0`: done
- `2`: the profile cannot be read
- `3`: `--root` is not a directory

## Examples

```sh
bondstone packs
bondstone packs --format json
```

## JSON output

```json
{"version": 1, "components": [{"kind": "pack", "id": "adr", "version": "1.0.0", "source": "bondstone-library",
                                "path": "...", "description": "...", "in_use": true}]}
```
