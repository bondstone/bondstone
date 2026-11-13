# Implementation Plan: Known violations

**Branch**: `v1-phase-5-known-violations` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-known-violations/spec.md`

## Summary

Give every diagnostic a key that names its problem without line numbers, record fingerprints
of rule, node and key in `.bondstone/known.json`, and let the policy step turn a matching
violation into info. Report entries that match nothing, and with `--base` entries that were
added. Add the diff clause `link_changed` and use it in the `speckit-capability` bridge.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: PyYAML, jsonschema (as before)

**Storage**: `.bondstone/known.json` in the repository

**Testing**: pytest, with throwaway git repositories for everything that needs a base

**Target Platform**: any platform with Python and git

**Project Type**: cli with a companion library package

**Performance Goals**: matching is a set lookup per diagnostic

**Constraints**: the fixed exit codes stay; `check` never writes; the file is only written by `baseline --known`

**Scale/Scope**: one module, two engine rules, one option pair, one diff clause, one bridge rule

## Constitution Check

The decision is ADR-006 (D6 of the design). Where the design leaves a point open, the choice
is listed under Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-known-violations/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
src/bondstone/
├── known.py                    # Entry, fingerprint, parse, render
├── schemas/known.schema.json
├── model.py                    # Diagnostic.key, Diagnostic.known
├── catalogue.py                # known-stale, known-grew; which engine rules accept known violations
├── config.py                   # loads known.json; allow_known on rules and lock entries; link_changed
├── rules/policy.py             # matching and stale entries
├── rules/diff.py               # growth since the base; the link_changed clause
├── rules/engine.py, node.py    # keys
├── baseline.py, cli.py         # baseline --known [--prune]
├── format.py                   # [known] and the summary
└── agent.py, context.py        # instructions, rules, explain, context

library/src/bondstone_library/packs/speckit-capability/   # the new rule, version 1.1.0
docs/capabilities/known-violations.md
tests/test_known.py, tests/test_rules_diff.py, library/tests/test_library.py
```

**Structure Decision**: `known.py` holds the file format and depends only on the model, so
the configuration can load it; what needs a check lives in `baseline.py` and the rules.

## Complexity Tracking

| Choice | Why | Alternative rejected |
| --- | --- | --- |
| An entry has `path` instead of `node` for a violation without a node | Files that are no documents and tags for unknown ids have no node | Leaving those violations unrecordable would block adoption on them |
| The change that adds the profile is not growth | Adoption in one commit needs no override that has to be removed again | Reporting every first `known.json` as growth |
| One `bondstone/known-grew` diagnostic, not one per entry | A regenerated file can add hundreds | One error per entry |
| Rules about a change or the configuration never accept known violations | An entry would silence every later breach on that node | Accepting any rule id in the file |
| `allow_known: false` both on a rule and in a preset's `lock` entry | Mirrors `locked`, which also exists in both places | Only one of the two |
| The key is not printed in JSON output | It would change every diagnostic for a value only the file needs | A `key` field in the output |
| `link_changed` compares with the base of the run | Diff rules know no earlier status of a node | "Became implemented in this range", which needs the derived status at the base |
