# Implementation Plan: SARIF output

**Branch**: `v1-phase-5-sarif` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-sarif-output/spec.md`

## Summary

A third output format for `check`. One module turns the diagnostics that text and JSON print
into a SARIF 2.1.0 log, with rule descriptions from the catalogue and from declared rules.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: none new

**Storage**: none

**Testing**: pytest with a golden file; the golden file was validated once against the published schema

**Target Platform**: any platform with Python and git

**Project Type**: cli with a companion library package

**Performance Goals**: not applicable

**Constraints**: deterministic output (no absolute paths, no timestamps); exit codes unchanged

**Scale/Scope**: one module, one option value

## Constitution Check

No new decision; SARIF output is part of phase 5 in the design.

## Project Structure

### Documentation (this feature)

```text
specs/005-sarif-output/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
src/bondstone/sarif.py      # the log: rules, results, suppressions, fingerprints
src/bondstone/cli.py        # `check --format sarif`
tests/test_sarif.py, tests/golden/check.sarif
.github/workflows/ci.yml    # keeps bondstone's own SARIF file as an artifact
```

**Structure Decision**: SARIF needs the configuration for rule descriptions, so it is its own
module and not a third function in `format.py`.

## Complexity Tracking

| Choice | Why | Alternative rejected |
| --- | --- | --- |
| Only the rules that reported are described | Small, and every result points at a rule | The whole catalogue in every file |
| An exempted violation keeps the rule `bondstone/exemption-used` | The same rule id as text and JSON | Reporting it under the exempted rule |
| The fingerprint is a hash of rule, node and key | The same identity as a known violation; stable when lines move | The line number |
| Paths are relative with `uriBaseId: %SRCROOT%` | The same file on every machine | Absolute `file://` URIs |
| CI stores the file as an artifact and does not upload it to code scanning | An upload needs another permission and publishes alerts | Uploading from this repository's workflow |
