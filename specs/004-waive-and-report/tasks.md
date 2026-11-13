---

description: "Task list for waive and report"
---

# Tasks: Waive and report

**Input**: Design documents from `/specs/004-waive-and-report/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: User Story 1 - report (Priority: P1)

- [x] T001 [US1] Counts of nodes, coverage, waivers and known violations in `src/bondstone/report.py`
- [x] T002 [US1] Exemptions per rule and per author with `--base`: `rule` in `exempted_by` (`src/bondstone/rules/diff.py`), the author of a commit (`src/bondstone/git.py`)
- [x] T003 [US1] The `report` command in `src/bondstone/cli.py` and `docs/cli/report.md`

## Phase 2: User Story 2 - waive (Priority: P2)

- [x] T004 [US2] Checks and the one-line edit of the profile in `src/bondstone/waive.py`
- [x] T005 [US2] The `waive` command in `src/bondstone/cli.py` and `docs/cli/waive.md`

## Phase 3: User Story 3 - output for agents (Priority: P2)

- [x] T006 [P] [US3] The error object for commands that stop, in `src/bondstone/cli.py`
- [x] T007 [P] [US3] `base` in the JSON output of `check --base`, in `src/bondstone/format.py` and `src/bondstone/cli.py`
- [x] T008 [P] [US3] The next item id in `context` and `new --dry-run`, in `src/bondstone/edit.py` and `src/bondstone/context.py`

## Phase 4: Polish

- [x] T009 Tests in `tests/test_report.py`, `tests/test_waive.py` and the files of the changed commands
- [x] T010 Requirements REQ-CLI-008, REQ-CLI-009 and REQ-PRF-016, the changed requirements, the command documents and the README
