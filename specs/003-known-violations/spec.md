---
# bondstone reads this block. Keep it at the very top of the file.
id: "003-known-violations"   # the name of this feature's folder under specs/
type: speckit:Feature
title: "Known violations"
modifies: [CAP-known-violations, CAP-diff-checks, CAP-spec-kit-adapter, CAP-profiles, CAP-rules, CAP-cli, CAP-agent-guidance, CAP-graph, CAP-code-traceability]     # capabilities this feature changes
delivers: [REQ-KNV-001, REQ-KNV-002, REQ-KNV-003, REQ-KNV-004, REQ-KNV-005, REQ-KNV-006, REQ-KNV-007, REQ-KNV-008, REQ-DIF-015, REQ-SKT-006]     # requirements this feature implements
decided_by: [ADR-006]   # decisions this feature rests on
---

# Feature Specification: Known violations

**Feature Branch**: `v1-phase-5-known-violations`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Adopt with known violations recorded in known.json"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Adopt a rule without fixing every old document first (Priority: P1)

A maintainer turns on bondstone, or a stricter rule, in a repository whose existing documents
break it. They record the current violations once. From then on `check` passes for the old
problems and fails for every new one.

**Why this priority**: Without it a repository either fixes everything first or lowers the
severity, which also removes the gate for new work.

**Independent Test**: Break a rule in an existing document, run `bondstone baseline --known`,
then add a second problem.

**Acceptance Scenarios**:

1. **Given** documents that break rules, **When** `bondstone baseline --known` runs, **Then** `.bondstone/known.json` has one entry per violation: rule, node and a key without line numbers.
2. **Given** a recorded violation, **When** `bondstone check` runs, **Then** it is reported as info, marked known, and the run passes.
3. **Given** a recorded violation in a document, **When** a new problem is added to that document, **Then** the new problem fails the run.

---

### User Story 2 - The record only shrinks (Priority: P1)

A reviewer can rely on `known.json` never hiding new debt: fixed problems leave it, and a
change that adds entries fails.

**Why this priority**: A baseline file that can be regenerated at will is a way around every rule.

**Independent Test**: Record a new violation on a branch and run `check --base`.

**Acceptance Scenarios**:

1. **Given** a fixed violation, **When** `bondstone check` runs, **Then** its entry is reported as `bondstone/known-stale` until `bondstone baseline --known --prune` removes it.
2. **Given** a committed `known.json`, **When** a change adds an entry, **Then** `check --base` reports `bondstone/known-grew` as an error.
3. **Given** a repository without a profile at the base, **When** one change adds the profile and `known.json`, **Then** nothing is reported as growth.

---

### User Story 3 - Some rules hold from the first day (Priority: P2)

An organisation's preset locks a rule and says that it accepts no known violations.

**Why this priority**: Less common, but without it a locked rule can be sidestepped on adoption.

**Independent Test**: Lock a rule with `allow_known: false` and record.

**Acceptance Scenarios**:

1. **Given** a preset with `lock: [{rule: adr/x, allow_known: false}]`, **When** `bondstone baseline --known` runs, **Then** violations of `adr/x` are not recorded and stay errors.
2. **Given** a rule declared with `allow_known: false`, **When** an entry names it, **Then** the entry is stale and the violation keeps its severity.

---

### User Story 4 - A finished feature is folded into its capabilities (Priority: P3)

A maintainer ticks the last task of a Spec Kit feature. The change must also update the
capabilities the feature modifies.

**Why this priority**: Carried over from the Spec Kit adapter; it needs a clause that diff
rules did not have.

**Independent Test**: Edit an implemented feature without editing a capability it modifies.

**Acceptance Scenarios**:

1. **Given** a diff rule with `link_changed: modifies`, **When** an implemented feature changes and a capability it modifies does not, **Then** the rule is reported on the feature and names the capability.
2. **Given** the `speckit-capability` bridge, **When** the same happens, **Then** `speckit-capability/implemented-feature-updates-its-capabilities` is a warning.

### Edge Cases

- A violation without a node, such as a file that is no document, is recorded by its path.
- Two identical problems in one node (the same broken target twice) share one entry.
- A waived violation is dropped before known violations are matched, so its entry is stale.
- Rules about a change (diff rules, lifecycles, immutability) and about the configuration are never recorded.
- A malformed `known.json` stops the check as a configuration error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `bondstone baseline --known` MUST record the current violations (REQ-KNV-001).
- **FR-002**: An entry MUST identify a violation without line numbers (REQ-KNV-002).
- **FR-003**: `check` MUST report a matching violation as info and fail on any other (REQ-KNV-003).
- **FR-004**: `check` MUST report entries that match nothing (REQ-KNV-004), and `--prune` MUST remove them without adding any (REQ-KNV-005).
- **FR-005**: `check --base` MUST report entries added since the base (REQ-KNV-006).
- **FR-006**: A rule or a preset's lock MUST be able to refuse known violations (REQ-KNV-007).
- **FR-007**: A malformed file MUST be a configuration error (REQ-KNV-008).
- **FR-008**: The generated agent instructions MUST forbid creating or extending the file (REQ-AGT-005).
- **FR-009**: Diff rules MUST have a clause for the link targets of a changed node (REQ-DIF-015), used by the `speckit-capability` bridge (REQ-SKT-006).

### Key Entities

- **Known violation**: rule, node or path, key.
- **`known.json`**: format version, the day it was first written, the entries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A repository whose documents break a newly adopted rule passes `check --base` after one `bondstone baseline --known`, without editing a document.
- **SC-002**: After that, one new violation fails `check`, and recording it fails `check --base`.
- **SC-003**: Every engine diagnostic that a node can raise more than once per rule has a key that tells the cases apart.

## Assumptions

- `bondstone report`, which counts the remaining entries per rule and per type, belongs to the next feature.
- The capability starts as `draft` and is activated after review.
