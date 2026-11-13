---
id: CLI-waive
type: cli:Command
title: waive
status: experimental
synopsis: bondstone waive [--format text|json] --reason REASON --expires DATE RULE [NODE]
json_output: true
implements: [CAP-profiles]
---

Adds a waiver to the profile: one exception from a rule, with a reason and the last day it applies.

The waiver is one new line under `waivers` in `.bondstone/profile.yaml`; nothing else in the file changes. A waiver is for an exception that should stay for a while. For problems that existed before a rule was adopted, use `bondstone baseline --known`.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `--reason REASON`: Why the exception is acceptable.
- `--expires DATE`: The last day it applies, as YYYY-MM-DD.
- `RULE`: A rule id such as adr/alternatives-considered.
- `NODE`: The node the waiver is for (default: every node).

## Exit codes

- `0`: the waiver was added
- `1`: refused, and nothing was changed: the rule is unknown or locked, the node does not exist, the reason is empty, the date is malformed or in the past, or the same waiver exists
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone waive adr/alternatives-considered ADR-004 --reason "Decided before we recorded alternatives." --expires 2027-06-30
bondstone waive bondstone/untyped-document --reason "The notes move to the wiki in March." --expires 2027-03-31
```

## JSON output

```json
{"version": 1, "rule": "adr/alternatives-considered", "node": "ADR-004",
 "reason": "Decided before we recorded alternatives.", "expires": "2027-06-30", "path": ".bondstone/profile.yaml"}
```

`node` is left out for a waiver that covers every node.
