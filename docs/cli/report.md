---
id: CLI-report
type: cli:Command
title: report
status: stable
synopsis: bondstone report [--format text|json] [--base REF]
json_output: true
implements: [CAP-cli]
---

Counts where the documentation stands: nodes by type and status, nodes traced to code, waivers and their state, known violations per rule and per type, and with `--base` the exemptions used since a commit.

The report never fails because of what it counts; `bondstone check` is the gate.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format text|json`: Output format (default: text).
- `--base REF`: Also count the exemptions used since REF.

## Exit codes

- `0`: the report was printed
- `2`: the configuration is invalid
- `3`: no profile, `--root` is not a directory, `--base` outside a git repository, or `REF` is not a commit

## Examples

```sh
bondstone report
bondstone report --base origin/main --format json
```

## JSON output

```json
{"version": 1,
 "nodes": {"total": 18, "by_type": {"adr:Decision": {"total": 3, "by_status": {"accepted": 2, "proposed": 1}}}},
 "coverage": {"capability:Requirement": {"needing_code": 12, "covered": 11}},
 "waivers": [{"rule": "adr/alternatives-considered", "node": "ADR-004", "reason": "...", "expires": "2027-06-30",
              "state": "active"}],
 "known": {"total": 2, "created": "2026-11-13", "by_rule": {"bondstone/section-missing": 2},
           "by_type": {"adr:Decision": 2}},
 "exemptions": {"base": "origin/main", "total": 1, "by_rule": {"starter/code-change-updates-living-spec": 1},
                "by_author": {"Ada": 1}}}
```

A waiver's `state` is `active`, `expiring` (it ends within 30 days), `expired`, `unused` or `invalid`. `coverage` lists the code-traceable types, counting the nodes in a status that needs code. In `known.by_type`, `(files)` stands for entries about a file. `exemptions` is only there with `--base`.
