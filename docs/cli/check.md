---
id: CLI-check
type: cli:Command
title: check
status: stable
synopsis: bondstone check [--format text|json] [--fail-on error|warn] [--base REF] [--no-exemptions]
json_output: true
implements: [CAP-cli, CAP-graph, CAP-rules, CAP-code-traceability, CAP-views, CAP-diff-checks]
---

Validates documents, links, rules, code tags and generated views; with `--base` also the changes since a commit.

`--base REF` compares the working tree, committed or not, with the merge base of `REF` and `HEAD`.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `--fail-on error|warn`: Lowest severity that fails the run (default: error).
- `--base REF`: Also check the changes since REF: lifecycles, immutability and diff rules.
- `--no-exemptions`: With --base, ignore the commit trailers that exempt a change from a diff rule.

## Exit codes

- `0`: no violation at or above `--fail-on`
- `1`: violations found
- `2`: the configuration is invalid; nothing was checked
- `3`: no profile, `--root` is not a directory, `--base` outside a git repository, or `REF` is not a commit

## Examples

```sh
bondstone check
bondstone check --base origin/main --format json
bondstone check --fail-on warn
```

## JSON output

```json
{"version": 1, "summary": {"errors": 1, "warnings": 0, "info": 0, "nodes": 15},
 "diagnostics": [{"rule": "bondstone/link-broken", "severity": "error", "path": "docs/x.md", "line": 5,
                  "node": "CAP-a", "message": "...", "hint": "..."}]}
```

`path`, `line`, `node`, `hint`, `fix` and `exempted_by` are left out when they do not apply.
