---

description: "Task list for known violations"
---

# Tasks: Known violations

**Input**: Design documents from `/specs/003-known-violations/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: User Story 1 - record and match (Priority: P1)

- [x] T001 [US1] `key` and `known` on diagnostics in `src/bondstone/model.py`; keys for engine diagnostics in `src/bondstone/rules/engine.py` and `src/bondstone/graph.py`, for declared rules in `src/bondstone/rules/node.py`
- [x] T002 [US1] The file format, its schema and fingerprints in `src/bondstone/known.py` and `src/bondstone/schemas/known.schema.json`
- [x] T003 [US1] Load the file with the configuration in `src/bondstone/config.py`; a malformed file is a configuration error
- [x] T004 [US1] Match in `src/bondstone/rules/policy.py`; mark known violations in `src/bondstone/format.py`
- [x] T005 [US1] `bondstone baseline --known` in `src/bondstone/baseline.py` and `src/bondstone/cli.py`

## Phase 2: User Story 2 - the record only shrinks (Priority: P1)

- [x] T006 [US2] `bondstone/known-stale` and `bondstone/known-grew` in `src/bondstone/catalogue.py`, `rules/policy.py` and `rules/diff.py`
- [x] T007 [US2] `bondstone baseline --known --prune`

## Phase 3: User Story 3 - rules that hold from the first day (Priority: P2)

- [x] T008 [US3] `allow_known: false` on a rule and in a preset's `lock` entry; engine rules about a change or the configuration never accept known violations
- [x] T009 [P] [US3] `bondstone rules` and `bondstone explain` say so; the agent instructions forbid creating or extending the file

## Phase 4: User Story 4 - link targets of a changed node (Priority: P3)

- [x] T010 [US4] The diff clause `link_changed` in `src/bondstone/config.py`, `rules/diff.py` and `context.py`
- [x] T011 [US4] `speckit-capability/implemented-feature-updates-its-capabilities`, bridge version 1.1.0, with a test on a git repository in `library/tests/test_library.py`

## Phase 5: Polish

- [x] T012 Tests in `tests/test_known.py` and `tests/test_rules_diff.py`
- [x] T013 `docs/capabilities/known-violations.md`, the capabilities whose code changed, and `docs/cli/baseline.md`
- [x] T014 Remove the waiver for ADR-006 and add the feature to release v1.0.0
- [x] T015 Show on a throwaway worktree of this repository that a stricter rule can be adopted with `baseline --known` and that a new violation still fails
