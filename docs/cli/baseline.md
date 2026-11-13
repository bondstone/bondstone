---
id: CLI-baseline
type: cli:Command
title: baseline
status: stable
synopsis: bondstone baseline [REF]
implements: [CAP-diff-checks]
---

Records in the profile the commit whose documents count as already adopted, so that the first `check --base` does not treat them as new.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `REF`: The commit (default: HEAD).

## Exit codes

- `0`: done
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory
- `3` also when the folder is no git repository or `REF` is not a commit

## Examples

```sh
bondstone baseline
bondstone baseline v0.9.0
```
