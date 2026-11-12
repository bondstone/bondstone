---

description: "Task list for the CLI and release packs"
---

# Tasks: CLI and release packs

**Input**: Design documents from `/specs/002-cli-and-release-packs/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: User Story 1 - commands (Priority: P1)

- [x] T001 [US1] `cli` pack with template and fixtures in `library/src/bondstone_library/packs/cli/`
- [x] T002 [P] [US1] `cli-capability` bridge with fixtures
- [x] T003 [US1] One document per command in `docs/cli/`, each tagged at its parser in `src/bondstone/cli.py`
- [x] T004 [US1] Test the documents against the argument parser in `tests/test_cli_docs.py`

## Phase 2: User Story 2 - releases (Priority: P2)

- [x] T005 [US2] `release` pack with template and fixtures in `library/src/bondstone_library/packs/release/`
- [x] T006 [P] [US2] `release-speckit` bridge with fixtures
- [x] T007 [US2] `docs/releases/v1.0.0.md` and the generated `CHANGELOG.md`

## Phase 3: Polish

- [x] T008 Describe the library's components in `docs/capabilities/library.md` and trace each to its manifest
- [ ] T009 Move the command documents to `stable` and activate CAP-library after review (follow-up pull request)
