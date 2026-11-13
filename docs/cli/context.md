---
id: CLI-context
type: cli:Command
title: context
status: experimental
synopsis: bondstone context [--format text|json] [--for PATH...] [--base REF]
json_output: true
implements: [CAP-agent-guidance]
---

Lists what to read before editing: the documents traced to the given files, the documents linked to those, and the diff rules that will fire.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `--for PATH`: Files or folders about to be edited.
- `--base REF`: The files changed since REF.

## Exit codes

- `0`: done
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory
- `1`: a path is outside the repository

## Examples

```sh
bondstone context --for src/app/reminders.py
bondstone context --base origin/main --format json
```

## JSON output

`version`, `paths`, `nodes` (one per node, with `id`, `type`, `path`, `line`, `title`, `status`, the `reasons` it is listed and, where there is one, a `note`) and `rules` (one per diff rule, with `id`, `severity`, `description`, `asks`, `must_change`, `hint` and `exempt`).
