---
# bondstone reads this block. Keep it at the very top of the file.
id: "005-sarif-output"   # the name of this feature's folder under specs/
type: speckit:Feature
title: "SARIF output"
modifies: [CAP-cli, CAP-profiles]     # capabilities this feature changes
delivers: [REQ-CLI-010]     # requirements this feature implements
decided_by: []   # decisions this feature rests on
---

# Feature Specification: SARIF output

**Feature Branch**: `v1-phase-5-sarif`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Print check results as SARIF"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See diagnostics where the change is reviewed (Priority: P1)

A team runs `bondstone check` in CI. With SARIF output the diagnostics appear as annotations
on the pull request and in the code-scanning view, on the line they are about, instead of
only in a job log.

**Why this priority**: It is the one output format that review tools read without a wrapper.

**Independent Test**: Run `bondstone check --format sarif` on a repository with violations
and validate the output against the SARIF 2.1.0 schema.

**Acceptance Scenarios**:

1. **Given** a repository with violations, **When** `bondstone check --format sarif` runs, **Then** the output is one SARIF 2.1.0 run with one result per diagnostic: rule, level, message, file and line.
2. **Given** a known violation or an exempted one, **When** the same runs, **Then** its result carries a suppression that says why.
3. **Given** an invalid configuration, **When** the same runs, **Then** the run is marked as not successful and the exit code is 2.

### Edge Cases

- A diagnostic without a line has a location without a region; one without a file has no location.
- Severity `info` becomes the level `note`.
- A result's fingerprint does not change when lines above it are added.
- Only `check` prints SARIF.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `bondstone check --format sarif` MUST print SARIF 2.1.0 (REQ-CLI-010).
- **FR-002**: The exit codes MUST be those of the other formats.
- **FR-003**: Known and exempted violations MUST be suppressed results.

### Key Entities

- **Result**: one diagnostic.
- **Rule descriptor**: what a rule checks and how to satisfy it, for the rules that reported.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The output validates against the published SARIF 2.1.0 schema.
- **SC-002**: The number of results equals the number of diagnostics of `--format json`.

## Assumptions

- Uploading the file to a code-scanning service is the job of the CI workflow, not of bondstone.
