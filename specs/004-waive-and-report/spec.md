---
# bondstone reads this block. Keep it at the very top of the file.
id: "004-waive-and-report"   # the name of this feature's folder under specs/
type: speckit:Feature
title: "Waive and report"
modifies: [CAP-cli, CAP-profiles, CAP-scaffolding, CAP-diff-checks, CAP-agent-guidance]     # capabilities this feature changes
delivers: [REQ-PRF-016, REQ-CLI-008, REQ-CLI-009]     # requirements this feature implements
decided_by: [ADR-005, ADR-006]   # decisions this feature rests on
---

# Feature Specification: Waive and report

**Feature Branch**: `v1-phase-5-waive-report`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Add waivers and report from the command line"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See where the documentation stands (Priority: P1)

A maintainer who adopted bondstone with known violations wants to plan the cleanup and see it
shrink. A team lead wants to know whether exemption trailers are used as a habit.

**Why this priority**: Known violations and exemptions are only safe when their use is visible.

**Independent Test**: Record known violations, run `bondstone report`, fix one, run it again.

**Acceptance Scenarios**:

1. **Given** a repository, **When** `bondstone report` runs, **Then** it counts nodes by type and status, nodes traced to code, waivers by state and known violations per rule and per type.
2. **Given** commits with exemption trailers since a ref, **When** `bondstone report --base REF` runs, **Then** it counts the exemptions per rule and per author.
3. **Given** a repository whose check fails, **When** `bondstone report` runs, **Then** it exits with 0.

---

### User Story 2 - Add a waiver without editing YAML (Priority: P2)

A maintainer grants one exception. The command checks the rule, the node and the date, and
adds one line to the profile.

**Why this priority**: The profile can be edited by hand; the command prevents waivers that
`check` would then report as invalid.

**Independent Test**: Waive a warning and run `check`.

**Acceptance Scenarios**:

1. **Given** a violation of a rule on a node, **When** `bondstone waive RULE NODE --reason R --expires D` runs, **Then** the profile has the waiver and the violation is no longer reported.
2. **Given** a locked rule, an unknown node or a date in the past, **When** `bondstone waive` runs, **Then** it is refused and the profile is unchanged.

---

### User Story 3 - An agent can tell what happened (Priority: P2)

Three gaps from the agent run of phase 3: a refused command and a failed check both exit with
1; `check --base` does not say what it compared; and nothing tells an agent the id of the
next item.

**Why this priority**: Each one made the agent guess.

**Independent Test**: Run the three commands with `--format json`.

**Acceptance Scenarios**:

1. **Given** a command that is refused, **When** it runs with `--format json`, **Then** standard output has `{"version": 1, "error": {"kind": "refused", "message": "..."}}`.
2. **Given** changes since a ref, **When** `check --base REF --format json` runs, **Then** the output has `base` with the ref, the commit and the changed files.
3. **Given** a capability with requirements up to REQ-AA-007, **When** `bondstone context --for` its file runs, **Then** the entry names `REQ-AA-008` as the next item id.
4. **Given** a type, **When** `bondstone new TYPE --title T --dry-run` runs, **Then** it prints the id and the path and creates nothing.

### Edge Cases

- A waiver without a node covers every node; violations without a node can only be waived that way.
- A profile whose `waivers` are written on one line is left to its author.
- A waiver that is both unused and about to expire is shown as unused.
- `bondstone graph` prints JSON by default, so a refused `graph` prints the error object.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `bondstone report` MUST print the counts as text or JSON (REQ-CLI-008).
- **FR-002**: `bondstone waive` MUST add a valid waiver or change nothing (REQ-PRF-016).
- **FR-003**: With `--format json`, a command that stops MUST print an error object (REQ-CLI-009).
- **FR-004**: `check --base --format json` MUST list what was compared (REQ-CLI-006).
- **FR-005**: `context` MUST name the next item id of a document, and `new --dry-run` the next id of a document type (REQ-AGT-003, REQ-SCF-001).

### Key Entities

- **Report**: nodes, coverage, waivers, known violations, exemptions.
- **Error object**: kind (`refused` or `environment`) and message.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After `baseline --known`, `report` shows the entries per rule and per type, and the numbers fall as violations are fixed and pruned.
- **SC-002**: A waiver added by the command is never reported as `bondstone/waiver-invalid`.
- **SC-003**: The exit codes 0 to 3 keep their meaning.

## Assumptions

- The exit codes of the design are fixed, so refused commands are told apart in JSON, not by a new code.
- The two new command documents start as `experimental`.
