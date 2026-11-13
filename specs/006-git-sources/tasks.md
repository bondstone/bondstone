---

description: "Task list for git sources"
---

# Tasks: Git sources

**Input**: Design documents from `/specs/006-git-sources/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: User Story 1 - share packs (Priority: P1)

- [x] T001 [US1] The syntax of a git source, the lock file with its schema, the cache and the hash of a component in `src/bondstone/sources.py`
- [x] T002 [US1] Fetch a ref or a commit and write a source's folder into the cache, in `src/bondstone/sources.py`
- [x] T003 [US1] Git sources in the resolver, between folders and installed packages, also from presets, in `src/bondstone/resolve.py`
- [x] T004 [US1] `bondstone update` in `src/bondstone/update.py` and `src/bondstone/cli.py`

## Phase 2: User Story 2 - a deterministic check (Priority: P1)

- [x] T005 [US2] A source that is not pinned is a configuration error; a cache that is behind is an environment error
- [x] T006 [US2] `bondstone update --locked`

## Phase 3: User Story 3 - move one pin (Priority: P2)

- [x] T007 [US3] `bondstone update NAME`

## Phase 4: Polish

- [x] T008 Tests against a remote in a temporary folder, in `tests/test_sources.py`
- [x] T009 REQ-PRF-017 to 020, `docs/cli/update.md`, the README and the agent instructions
- [x] T010 `bondstone update --locked` in CI before the checks; remove the waiver for ADR-011
