---
id: CAP-rules
title: Rules and traits
status: active
owner: dworek
code: RUL
depends_on: [CAP-graph]
constrained_by: [ADR-002, ADR-004, ADR-005]
---

## Purpose

Evaluate declarative rules from packs, bridges and the profile, and the checks implied by traits.

## Requirements

### REQ-RUL-001: Select nodes

Rule selectors SHALL match nodes by type, role, trait, status and field values, combined with AND.

#### Scenario: Status selector

- Given a rule with `when: {type: Solution, status: committed}`
- When a solution is `idea`
- Then the rule does not apply to it

### REQ-RUL-002: Evaluate requirement clauses

Bondstone SHALL support `link` (with `min` or `all`), `incoming`, `field`, `section` and `contains` clauses and report each failing clause with the rule's message.

#### Scenario: All targets must match

- Given a clause `link: constrained_by, all: true, to: {status: accepted}`
- When one target is superseded
- Then the rule fails and names that target

### REQ-RUL-003: Validate frontmatter against the type schema

Bondstone SHALL validate fields against the type's JSON Schema, including `status` values from the lifecycle trait and `owner` from the owned trait.

#### Scenario: Unknown status

- Given a decision with `status: approved`
- When check runs
- Then `bondstone/field-invalid` is reported

### REQ-RUL-004: Check supersession

For supersedable types Bondstone SHALL require superseded targets to have status `superseded`, allow one successor per document and reject cycles.

#### Scenario: Successor without status change

- Given ADR-002 supersedes ADR-001
- When ADR-001 is still accepted
- Then `bondstone/supersede-status` is reported

### REQ-RUL-005: Require sections

Bondstone SHALL report documents that lack a section their type requires.

#### Scenario: Missing section

- Given a decision without `## Consequences`
- When check runs
- Then `bondstone/section-missing` is reported

### REQ-RUL-006: Flag unfinished placeholders

Bondstone SHALL report `<!-- todo: ... -->` markers outside code spans as a warning in a document's initial status and as an error otherwise.

#### Scenario: Placeholder in an accepted decision

- Given an accepted decision with a todo marker
- When check runs
- Then `bondstone/todo-left` is an error
