---
# bondstone reads this block. Keep it at the very top of the file.
id: "001-spec-kit-adapter"   # the name of this feature's folder under specs/
type: speckit:Feature
title: "Spec Kit adapter"
modifies: [CAP-graph, CAP-diff-checks, CAP-spec-kit-adapter]     # capabilities this feature changes
delivers: [REQ-GRA-010, REQ-GRA-011, REQ-DIF-014, REQ-SKT-001, REQ-SKT-002, REQ-SKT-003, REQ-SKT-004, REQ-SKT-005]     # requirements this feature implements
decided_by: [ADR-007, ADR-013, ADR-015, ADR-017]   # decisions this feature rests on
---

# Feature Specification: Spec Kit adapter

**Feature Branch**: `v1-phase-4-speckit`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "Make Spec Kit features part of bondstone's graph and gate bondstone's own changes on them"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A feature folder is checked like any other document (Priority: P1)

A team plans a change with Spec Kit. The folder `specs/NNN-name/` shows up in `bondstone
check` as one node, with a status that follows the work without anyone writing it down.

**Why this priority**: Every rule about features needs the node and its status first.

**Independent Test**: Create a feature folder with `spec.md`, add `plan.md`, tick the tasks in
`tasks.md`, and read the status from `bondstone graph` after each step.

**Acceptance Scenarios**:

1. **Given** a folder with only `spec.md`, **When** `bondstone check` runs, **Then** the feature is `specified`.
2. **Given** a `tasks.md` with one open task, **When** `bondstone check` runs, **Then** the feature is `planned`, and `implemented` once that task is ticked.
3. **Given** a feature whose `id` differs from its folder's name, **When** `bondstone check` runs, **Then** `bondstone/id-path` names the expected folder.

---

### User Story 2 - A finished feature is folded into the living documentation (Priority: P1)

When the last task of a feature is ticked, bondstone checks that the requirements it delivers
are active and tagged in code, and that the decisions it rests on are accepted.

**Why this priority**: This is the reason to connect Spec Kit at all (D7): a per-change record
that is not folded into the capabilities leaves them stale.

**Independent Test**: Tick the last task of a feature that delivers a requirement with
`Status: planned`, and see the check fail.

**Acceptance Scenarios**:

1. **Given** an implemented feature that delivers a planned requirement, **When** `bondstone check` runs, **Then** it fails with `speckit-capability/implemented-feature-delivers-covered-requirements`.
2. **Given** an implemented feature that names a proposed decision, **When** `bondstone check` runs, **Then** it fails with `speckit-adr/implemented-feature-rests-on-accepted-decisions`.

---

### User Story 3 - Spec Kit writes the frontmatter bondstone needs (Priority: P2)

A team installs one Spec Kit preset. From then on `/speckit.specify` creates `spec.md` with
the frontmatter block, and the command tells the agent how to fill it in.

**Why this priority**: Without it every feature needs the block by hand, which works but is
easy to forget.

**Independent Test**: In a fresh Spec Kit 1.4.0 project, install the preset and create a
feature with Spec Kit's own script; the file starts with the block.

**Acceptance Scenarios**:

1. **Given** a Spec Kit project with the preset, **When** a feature is created, **Then** `spec.md` starts with `id`, `type: speckit:Feature`, `title` and the three links.
2. **Given** the preset, **When** `specify preset resolve spec-template` runs, **Then** it shows the block as a `prepend` layer on the core template.

---

### User Story 4 - Bondstone's own changes need a feature (Priority: P2)

A pull request to bondstone that changes source code without touching a feature under
`specs/` fails CI.

**Why this priority**: It is the exit criterion of phase 4, and it proves the adapter on a
real project.

**Independent Test**: Change a source file on a branch and run `bondstone check --base`.

**Acceptance Scenarios**:

1. **Given** a change to `src/bondstone/` and nothing under `specs/`, **When** `bondstone check --base origin/v1` runs, **Then** `starter-speckit/source-change-has-feature` is an error.
2. **Given** the same change with a ticked task in a feature's `tasks.md`, **When** the check runs, **Then** the rule is satisfied.

### Edge Cases

- A `tasks.md` without any checkbox does not make a feature `implemented`.
- A `status` written in a feature's frontmatter is an error, because two sources would disagree.
- A feature created with Spec Kit's `--timestamp` numbering still matches the id template.
- `plan.md` and `tasks.md` have no frontmatter; they must not be reported as untyped documents.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bondstone MUST read `specs/<id>/spec.md` as one `speckit:Feature` (REQ-SKT-001).
- **FR-002**: Bondstone MUST derive a feature's status from `spec.md`, `plan.md` and the task list in `tasks.md` (REQ-GRA-011).
- **FR-003**: Bondstone MUST report a document whose path does not carry its id (REQ-GRA-010).
- **FR-004**: A change to `plan.md` or `tasks.md` MUST count as a change to the feature (REQ-DIF-014).
- **FR-005**: The library MUST ship a Spec Kit preset that adds the frontmatter block, pinned to the tested Spec Kit release (REQ-SKT-002).
- **FR-006**: An implemented feature MUST deliver only active, tagged requirements (REQ-SKT-003) and rest only on accepted decisions (REQ-SKT-004).
- **FR-007**: The `starter-speckit` preset MUST ask for a changed feature when code changes (REQ-SKT-005).
- **FR-008**: Bondstone's own profile MUST extend `starter-speckit` with that rule as an error.

### Key Entities

- **Feature**: one folder under `specs/`; id, title, derived status, links `modifies`, `delivers`, `decided_by`.
- **Companion file**: `plan.md` or `tasks.md`; no node of its own, part of its feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `bondstone check --fail-on warn` passes on bondstone's own repository with the profile on `starter-speckit`.
- **SC-002**: A pull request that changes source code without a feature fails `bondstone check --base` in CI.
- **SC-003**: In a fresh Spec Kit 1.4.0 project with the preset, a new `spec.md` needs only its placeholders filled to pass `bondstone check`.

## Assumptions

- Spec Kit 1.4.0 is the tested release; later releases need the check in the pack's README again.
- Features are created by Spec Kit's commands, not by `bondstone new`.
- The preset is written by hand; generating it from the packs is planned for phase 6.
