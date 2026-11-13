---

description: "Task list for the Spec Kit adapter"
---

# Tasks: Spec Kit adapter

**Input**: Design documents from `/specs/001-spec-kit-adapter/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

## Phase 1: Foundational (engine)

- [x] T001 [US1] Add the `derived-status` trait to `src/bondstone/schemas/pack.schema.json` and validate it in `src/bondstone/config.py`
- [x] T002 [US1] Derive the status and remember companion files in `src/bondstone/graph.py`
- [x] T003 [US1] Report `bondstone/id-path` in `src/bondstone/rules/engine.py` and add it to `src/bondstone/catalogue.py`
- [x] T004 [US4] Count a companion change as a change to the document in `src/bondstone/rules/diff.py`
- [x] T005 [P] [US1] Refuse `bondstone status` for a derived status in `src/bondstone/edit.py`; describe it in `src/bondstone/agent.py`
- [x] T006 [P] [US1] Tests in `tests/test_derived_status.py` and `tests/test_rules_engine.py`

## Phase 2: User Story 1 and 2 - pack and bridges (Priority: P1)

- [x] T007 [US1] `speckit` pack with fixtures in `library/src/bondstone_library/packs/speckit/`
- [x] T008 [P] [US2] `speckit-capability` bridge with fixtures
- [x] T009 [P] [US2] `speckit-adr` bridge with fixtures

## Phase 3: User Story 3 - Spec Kit preset (Priority: P2)

- [x] T010 [US3] Spec Kit preset in `library/src/bondstone_library/packs/speckit/spec-kit/`
- [x] T011 [US3] Verify it in a fresh Spec Kit 1.4.0 project: `specify preset add --dev`, `specify preset resolve spec-template`, `create-new-feature.sh`
- [x] T012 [US3] Tests that keep the preset, the pack and the bridges in step in `library/tests/test_library.py`

## Phase 4: User Story 4 - bondstone's own gate (Priority: P2)

- [x] T013 [US4] `starter-speckit` preset with a fixture
- [x] T014 [US4] Bondstone's profile extends `starter-speckit` with `source-change-has-feature` as an error
- [x] T015 [US4] Set up Spec Kit in this repository with the preset installed
- [x] T016 [US4] Record the decisions in ADR-017 and the behaviour in `docs/capabilities/spec-kit-adapter.md`

## Phase 5: Polish

- [ ] T017 Accept ADR-017 and activate CAP-spec-kit-adapter after review (follow-up pull request)
