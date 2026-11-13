---
# bondstone reads this block. Keep it at the very top of the file.
id: "002-cli-and-release-packs"   # the name of this feature's folder under specs/
type: speckit:Feature
title: "CLI and release packs"
modifies: [CAP-library]     # capabilities this feature changes
delivers: [REQ-LIB-001, REQ-LIB-002, REQ-LIB-003, REQ-LIB-004, REQ-LIB-005, REQ-LIB-006, REQ-LIB-007, REQ-LIB-008, REQ-LIB-009]     # requirements this feature implements
decided_by: [ADR-012]   # decisions this feature rests on
---

# Feature Specification: CLI and release packs

**Feature Branch**: `v1-phase-4-cli-release`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "Document every bondstone command and release with library packs"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every command has a reference document that cannot go stale (Priority: P1)

A maintainer adds an option to a command. The command's document under `docs/cli/` is where
the option is described, and a test fails when the document does not mention it.

**Why this priority**: The command line is bondstone's public surface.

**Independent Test**: Add an argument to a subparser and run the tests.

**Acceptance Scenarios**:

1. **Given** the argument parser, **When** the tests run, **Then** every subcommand has a `cli:Command` document whose synopsis and options name every option of the parser.
2. **Given** a stable command without a tag in code, **When** `bondstone check` runs, **Then** `cli/stable-command-is-implemented` is an error.
3. **Given** a stable command that implements no capability, **When** `bondstone check` runs, **Then** `cli-capability/stable-command-implements-capability` is an error.

---

### User Story 2 - A release lists the features it ships (Priority: P2)

A maintainer plans a version in `docs/releases/`, lists the features it includes, and gets
`CHANGELOG.md` generated. A version cannot be marked released while a feature in it is open.

**Why this priority**: Releases are rarer than commands, but the changelog should not be
written by hand.

**Independent Test**: Mark a release as released while one of its features has an open task.

**Acceptance Scenarios**:

1. **Given** release documents, **When** `bondstone gen` runs, **Then** `CHANGELOG.md` lists them.
2. **Given** a released version that includes a feature with an open task, **When** `bondstone check` runs, **Then** `release-speckit/release-includes-only-implemented` is an error.

### Edge Cases

- A nested command such as `profile check` has the id `CLI-profile-check`.
- A planned release may include features that are not implemented yet.
- A pre-release version such as `1.0.0a1` is a valid release id.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST ship a `cli` pack with one document per command (REQ-LIB-001).
- **FR-002**: The library MUST ship a bridge that ties stable commands to active capabilities (REQ-LIB-002).
- **FR-003**: The library MUST ship a `release` pack that generates `CHANGELOG.md` (REQ-LIB-003).
- **FR-004**: The library MUST ship a bridge that ties releases to implemented features (REQ-LIB-004).
- **FR-005**: Every component of the library MUST have fixtures that `bondstone pack test` runs (REQ-LIB-005).
- **FR-006**: Bondstone MUST document each of its own commands and its next release with these packs.

### Key Entities

- **Command**: one subcommand; title, synopsis, status, the capabilities it implements.
- **Release**: one version; title, version, date, status, the features it includes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All fifteen bondstone commands have a document, and a test compares each with the argument parser.
- **SC-002**: `CHANGELOG.md` is generated and checked for staleness like any other view.
- **SC-003**: The fixtures of the four new components pass in CI.

## Assumptions

- New command documents start as `experimental`; a later change moves them to `stable`.
- The command documents were first written from the argument parser and are maintained by hand from now on.
