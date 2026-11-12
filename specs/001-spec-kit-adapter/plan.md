# Implementation Plan: Spec Kit adapter

**Branch**: `v1-phase-4-speckit` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-spec-kit-adapter/spec.md`

## Summary

Make a Spec Kit feature folder one node of the graph. The engine gains a trait that derives a
status from files and a rule that ties an id to its path. The library gains the `speckit`
pack, two bridges, the `starter-speckit` preset and a Spec Kit preset for the frontmatter.
Bondstone's own profile moves to `starter-speckit`, so its CI asks for a feature.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: PyYAML, jsonschema; Spec Kit 1.4.0 for the preset (not a Python dependency)

**Storage**: files in the repository

**Testing**: pytest; fixtures run by `bondstone pack test`

**Target Platform**: any platform with Python and git

**Project Type**: cli with a companion library package

**Performance Goals**: no measurable change to `bondstone check`

**Constraints**: the engine ships no packs (ADR-012); every document states its type (ADR-015)

**Scale/Scope**: one trait, one engine rule, one pack, two bridges, two presets

## Constitution Check

The project has no constitution yet beyond its design and decisions. The plan follows them:
the engine learns nothing about Spec Kit (principle 1); everything specific to it is in the
library.

## Project Structure

### Documentation (this feature)

```text
specs/001-spec-kit-adapter/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
src/bondstone/
├── graph.py            # derived status, companion files
├── config.py           # trait validation, path pattern of an id
├── rules/engine.py     # bondstone/id-path
├── rules/diff.py       # a companion change is a change to the document
└── schemas/pack.schema.json

library/src/bondstone_library/packs/
├── speckit/            # pack, README, Spec Kit preset in spec-kit/
├── speckit-capability/ # bridge
├── speckit-adr/        # bridge
└── starter-speckit/    # preset

tests/test_derived_status.py
library/tests/test_library.py
```

**Structure Decision**: The trait and the rule are generic and live in the engine. The pack,
the bridges and both kinds of preset live in the library, each with fixtures.

## Complexity Tracking

No deviations to justify.
