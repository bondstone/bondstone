# Implementation Plan: CLI and release packs

**Branch**: `v1-phase-4-cli-release` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-cli-and-release-packs/spec.md`

## Summary

Port the POC's `cli` and `release` packs to the v1 formats, connect them with the bridges
`cli-capability` and `release-speckit`, and use them on bondstone itself: one document per
command, one release document, a generated changelog.

## Technical Context

**Language/Version**: Python 3.11+ (tests only; the components are YAML)

**Primary Dependencies**: none beyond the engine

**Storage**: files in the repository

**Testing**: pytest; fixtures run by `bondstone pack test`

**Target Platform**: any platform with Python and git

**Project Type**: cli with a companion library package

**Performance Goals**: not applicable

**Constraints**: the engine ships no packs (ADR-012); no engine change is needed

**Scale/Scope**: two packs, two bridges, fifteen command documents, one release document

## Constitution Check

The plan adds no engine behaviour. Everything is expressed with existing traits, rules and views.

## Project Structure

### Documentation (this feature)

```text
specs/002-cli-and-release-packs/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
library/src/bondstone_library/packs/
├── cli/                # pack, template, fixtures
├── cli-capability/     # bridge, fixtures
├── release/            # pack, template, fixtures
└── release-speckit/    # bridge, fixtures

src/bondstone/cli.py    # one tag per command, at its parser
docs/cli/               # one document per command
docs/releases/          # the next release
tests/test_cli_docs.py  # documents against the argument parser
```

**Structure Decision**: Components live in the library; bondstone's own documents live under `docs/`.

## Complexity Tracking

No deviations to justify.
