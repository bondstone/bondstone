---
id: CLI-gen
type: cli:Command
title: gen
status: stable
synopsis: bondstone gen
implements: [CAP-views]
---

Writes every generated view that is missing or out of date.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).

## Exit codes

- `0`: done
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone gen
```
