---
id: CAP-diff-checks
title: Checks against a git base
status: draft
owner: dworek
code: DIF
depends_on: [CAP-graph, CAP-rules]
constrained_by: [ADR-005]
---

## Purpose

With `--base REF`, compare documents and code with an earlier version to enforce how they may change.

## Requirements

### REQ-DIF-001: Enforce status transitions

Bondstone SHALL report status changes that the type's lifecycle transitions do not allow.

#### Scenario: Skipping a step

- Given a proposal that was draft
- When it becomes implemented
- Then `bondstone/status-transition` is reported

### REQ-DIF-002: Protect immutable documents

Bondstone SHALL report any change other than allowed fields to a document whose previous status is listed in its immutable trait.

#### Scenario: Editing an accepted decision

- Given ADR-001 was accepted
- When its decision text changes
- Then `bondstone/immutable` is reported

### REQ-DIF-003: Start new documents in a creation status

Bondstone SHALL report a new document whose status is not in its lifecycle's `create_as` list (default: the initial status).

#### Scenario: Created as accepted

- Given no ADR-002 at the base
- When ADR-002 is added with status accepted
- Then `bondstone/status-initial` is reported

### REQ-DIF-004: Follow renames

Bondstone SHALL compare a renamed or moved document with its previous version instead of treating it as new.

#### Scenario: Moved file

- Given ADR-001 moved to a new filename without git mv
- When check runs with a base
- Then no status-initial error is reported

### REQ-DIF-005: Run on-change rules

Rules with `on_change` SHALL run only when changed files match their globs, and `changed` clauses SHALL count changed documents that match a selector.

#### Scenario: Code without a spec change

- Given a rule requiring a changed living spec for `src/**`
- When only code changes
- Then the rule fails

### REQ-DIF-006: Require the traced specs to change

A `changed` clause with `traced: true` SHALL require every matching document tagged in the changed code, now or at the base, to change, and SHALL fall back to `min` for untagged code.

#### Scenario: Wrong spec changed

- Given code tagged REQ-AA-001 changes
- When only CAP-b changes
- Then the rule fails for CAP-a
