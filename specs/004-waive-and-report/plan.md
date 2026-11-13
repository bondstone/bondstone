# Implementation Plan: Waive and report

**Branch**: `v1-phase-5-waive-report` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-waive-and-report/spec.md`

## Summary

Two commands and three additions to existing output. `report` counts what the graph, the
profile and `known.json` already hold. `waive` adds one line to the profile after checking
what `check` would reject. Commands that stop print an error object with `--format json`,
`check --base` lists the compared files in JSON, and next ids are available from `context`
and `new --dry-run`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: PyYAML, jsonschema (as before)

**Storage**: `.bondstone/profile.yaml` (one added line)

**Testing**: pytest, with throwaway git repositories for exemptions and compared files

**Target Platform**: any platform with Python and git

**Project Type**: cli with a companion library package

**Performance Goals**: `report` runs one check

**Constraints**: exit codes 0 to 3 keep their meaning; JSON changes are additions; the profile is edited one line at a time

**Scale/Scope**: two modules, two commands, three additions

## Constitution Check

No new decision. Exemptions are counted as ADR-005 asks, known violations as ADR-006 asks.

## Project Structure

### Documentation (this feature)

```text
specs/004-waive-and-report/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
src/bondstone/
├── report.py         # the counts, as text and JSON
├── waive.py          # checks, and the one-line edit of the profile
├── cli.py            # waive, report, new --dry-run, the error object, `base` in check JSON
├── format.py         # `base` in JSON output
├── edit.py           # next item id; dry run
├── context.py        # next_item_id per document
├── git.py            # the author of a commit
└── rules/diff.py     # exempted_by names the rule

docs/cli/waive.md, docs/cli/report.md
tests/test_waive.py, tests/test_report.py
```

**Structure Decision**: One module per command; the profile edit follows `baseline.py`, which
also changes single lines.

## Complexity Tracking

| Choice | Why | Alternative rejected |
| --- | --- | --- |
| `waive` takes NODE as optional | A violation without a node can only be waived for every node | A required NODE, as the design's synopsis shows |
| Error object on stdout, exit codes unchanged | The design fixes the codes 0 to 3 | A new exit code for refused commands |
| `exempted_by` gains `rule` | `report` counts exemptions per rule; the diagnostic's own rule is `bondstone/exemption-used` | Parsing the message |
| Next item id in `context`, next document id by `new --dry-run` | Items are added by hand, documents by `new` | A separate `next-id` command |
| `expiring` means within 30 days | A fixed, documented window | A profile setting |
