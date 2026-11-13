---
id: CLI-baseline
type: cli:Command
title: baseline
status: stable
synopsis: bondstone baseline [REF] [--known [--prune]]
implements: [CAP-diff-checks, CAP-known-violations]
---

Records in the profile the commit whose documents count as already adopted, so that the first `check --base` does not treat them as new.

With `--known` it records the current violations in `.bondstone/known.json` instead: `check` then reports them as info, and only new violations fail. The file may only shrink; `check --base` reports entries added since the base as `bondstone/known-grew`.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `REF`: The commit (default: HEAD).
- `--known`: Record the current violations in .bondstone/known.json instead of a commit.
- `--prune`: With --known, only remove the entries that no longer occur.

## Exit codes

- `0`: done
- `1`: `--prune` without `--known`, or `--known` with a `REF`
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory
- `3` also when the folder is no git repository or `REF` is not a commit

## Examples

```sh
bondstone baseline
bondstone baseline v0.9.0
bondstone baseline --known
bondstone baseline --known --prune
```
