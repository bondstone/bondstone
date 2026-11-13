---
id: CLI-check
type: cli:Command
title: check
status: stable
synopsis: bondstone check [--format text|json|sarif] [--fail-on error|warn] [--base REF] [--no-exemptions]
json_output: true
implements: [CAP-cli, CAP-graph, CAP-rules, CAP-code-traceability, CAP-views, CAP-diff-checks]
---

Validates documents, links, rules, code tags and generated views; with `--base` also the changes since a commit.

`--base REF` compares the working tree, committed or not, with the merge base of `REF` and `HEAD`.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json|sarif`: Output format (default: text); sarif is SARIF 2.1.0 for code-scanning tools.
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
bondstone check --format sarif > bondstone.sarif
```

## JSON output

```json
{"version": 1, "summary": {"errors": 1, "warnings": 0, "info": 0, "nodes": 15},
 "diagnostics": [{"rule": "bondstone/link-broken", "severity": "error", "path": "docs/x.md", "line": 5,
                  "node": "CAP-a", "message": "...", "hint": "..."}]}
```

`path`, `line`, `node`, `hint`, `fix`, `exempted_by` and `known` are left out when they do not apply.

With `--base` the object also has `base`, between `summary` and `diagnostics`: the `ref` that was given, the `commit` the working tree was compared with (the merge base), and `changes`, one `{path, kind}` per file that differs, with `old_path` for a renamed file.

```json
"base": {"ref": "origin/main", "commit": "92cbf1b…", "changes": [{"path": "src/a.py", "kind": "modified"}]}
```

## SARIF output

`--format sarif` prints one SARIF 2.1.0 run with one result per diagnostic: the rule, the level (`error`, `warning`, or `note` for info), the message with its hint, the file and line, and a fingerprint that does not change when lines move. The rules that reported are described under `tool.driver.rules`. A known violation and an exempted one carry a `suppressions` entry that says why. A configuration error is a run with `executionSuccessful: false`.

When the check could not run, the JSON object is `{"version": 1, "error": {"kind": "environment", "message": "..."}}` and the exit code is 3.
