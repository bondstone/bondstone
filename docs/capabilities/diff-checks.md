---
id: CAP-diff-checks
title: Checks against a git base
status: active
owner: dworek
code: DIF
depends_on: [CAP-graph, CAP-rules]
constrained_by: [ADR-005, ADR-008]
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

Rules with `on_change` SHALL run only when changed files match their globs, `changed` clauses SHALL count changed documents that match a selector, and `exists` clauses SHALL count all documents that match a selector.

#### Scenario: Code without a spec change

- Given a rule requiring a changed living spec for `src/**`
- When only code changes
- Then the rule fails

#### Scenario: Work under an accepted proposal

- Given a rule requiring `exists: {role: change, status: accepted}` for `src/**`
- When only code changes and a proposal is accepted
- Then the rule passes

### REQ-DIF-006: Require the traced specs to change

A `changed` clause with `traced: true` SHALL require every matching document tagged in the changed regions of the code to change, and SHALL fall back to `min` when no tagged region changed. A tag's region is the code it annotates: from its block of consecutive tag lines to the end of the block of code below it (before the next line at the same or lower indentation that follows a blank line, or before the next tag block at the same or lower indentation; tags inside the block nest). Regions are taken in the current file for changed lines and in the base file for removed lines; changes to tag lines alone do not count.

#### Scenario: Wrong spec changed

- Given code tagged REQ-AA-001 changes
- When only CAP-b changes
- Then the rule fails for CAP-a

#### Scenario: Change in another function

- Given a file with a REQ-AA-001 region and a REQ-BB-001 region
- When only the REQ-BB-001 region changes
- Then only CAP-b has to change

#### Scenario: Tag inside a function

- Given a function tagged REQ-AA-001 with a tag ENG-001 inside its body
- When a line below the inner block changes
- Then CAP-a has to change

### REQ-DIF-007: Compare adopted documents with the baseline

When a document is missing at the base but exists with the same id at the profile's `baseline` commit, Bondstone SHALL compare it with its baseline version (transitions and immutability) instead of treating it as new.

#### Scenario: Adoption pull request

- Given ADR-001 is accepted at the baseline and missing on main
- When check runs with `--base main`
- Then no status-initial error is reported for ADR-001

#### Scenario: Edited after the baseline

- Given ADR-001 was accepted at the baseline
- When its decision text changes and check runs with `--base main`
- Then `bondstone/immutable` is reported

### REQ-DIF-008: Report a missing baseline commit

Bondstone SHALL report an error, with a fix hint, when the baseline commit is not available in the clone.

#### Scenario: Shallow clone

- Given a profile baseline that is not in the clone
- When check runs with a base
- Then `bondstone/baseline-missing` is reported

### REQ-DIF-009: Set the baseline

`bondstone baseline [REF]` SHALL resolve REF (default HEAD) to a commit and record it, quoted, as the profile's `baseline`.

#### Scenario: Adopting bondstone

- Given a repository with existing documents
- When `bondstone baseline` runs
- Then the profile contains `baseline: '<commit>'`
