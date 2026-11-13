---

description: "Task list for SARIF output"
---

# Tasks: SARIF output

**Input**: Design documents from `/specs/005-sarif-output/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: User Story 1 - SARIF (Priority: P1)

- [x] T001 [US1] Results, rule descriptions, suppressions and fingerprints in `src/bondstone/sarif.py`
- [x] T002 [US1] `check --format sarif`, also for configuration errors, in `src/bondstone/cli.py`
- [x] T003 [US1] Tests and a golden file in `tests/test_sarif.py` and `tests/golden/check.sarif`

## Phase 2: Polish

- [x] T004 REQ-CLI-010, `docs/cli/check.md` and the README section on CI
- [x] T005 Keep bondstone's own SARIF file as an artifact in `.github/workflows/ci.yml`
