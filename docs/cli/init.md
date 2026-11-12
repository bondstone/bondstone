---
id: CLI-init
type: cli:Command
title: init
status: experimental
synopsis: bondstone init [--preset NAME]
implements: [CAP-profiles]
---

Creates `.bondstone/profile.yaml` in the current folder or under `--root`: empty, or extending a preset.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--preset NAME`: Extend this preset, such as `starter`.

## Exit codes

- `0`: the profile was created
- `1`: a profile exists already, or the preset is not available
- `3`: `--root` is not a directory

## Examples

```sh
bondstone init
bondstone init --preset starter
```
