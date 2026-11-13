---

description: "Task list for private git sources"
---

# Tasks: Private git sources

**Input**: Design documents from `/specs/007-private-sources/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: User Story 1 - private repositories (Priority: P1)

- [x] T001 [US1] Take git's reason line and remove credentials from it, in `src/bondstone/sources.py`
- [x] T002 [US1] Explain a repository that git cannot read, also for a pinned commit with `update --locked`
- [x] T003 [US1] Tests in `tests/test_sources.py`
- [x] T004 [US1] Try it against a private GitHub repository: with a credential helper, without credentials, and with a token in the URL

## Phase 2: Polish

- [x] T005 REQ-PRF-020, "Private sources" in `docs/cli/update.md`, and the README
