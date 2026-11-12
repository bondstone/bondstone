---
id: CAP-code-traceability
type: capability:Capability
title: Code traceability
status: active
owner: dworek
code: TRC
constrained_by: [ADR-009]
depends_on: [CAP-graph]
---

## Purpose

Code points at the documents it implements with a comment, `bondstone: REQ-REM-001`. Bondstone
checks that every tag names something that exists, that what should be implemented is tagged
somewhere, and it knows which lines of code belong to which tag.

## Requirements

### REQ-TRC-001: Find tags in code

Bondstone SHALL find every `bondstone: ID` tag in the files that match the profile's
`code.include` globs and not its `code.exclude` globs, whatever the comment syntax of the
language. One tag may list several ids separated by commas. An id MUST start with a capital
letter, so that prose such as `bondstone: the tool` is not a tag.

#### Scenario: Two ids in one tag

- Given the line `// bondstone: REQ-REM-001, REQ-REM-002` in a Dart file
- When the graph is built
- Then both requirements are covered

### REQ-TRC-002: Know the region of code a tag annotates

Bondstone SHALL treat the block of code below a tag as the tag's region. Tags on consecutive
lines share a region. The region MUST end before the next tag at the same or a lower
indentation, or before the first line that follows a blank line and is indented no deeper than
the first code line. A tag deeper inside the code has a region of its own and does not end the
outer one.

#### Scenario: Two tagged functions

- Given a file with a tag above each of two functions
- When regions are computed
- Then the first tag's region ends at the last line of the first function

### REQ-TRC-003: Reject tags that point nowhere

Bondstone SHALL report a tag whose id does not exist as `bondstone/code-ref-unknown`, and a
tag on a node whose type lacks the `code-traceable` trait as `bondstone/code-ref-not-traceable`,
whatever the node's status.

#### Scenario: Tag for a requirement that does not exist

- Given the tag `bondstone: REQ-HAB-009` and no such requirement
- When `bondstone check` runs
- Then `bondstone/code-ref-unknown` is reported at the tag's line

### REQ-TRC-004: Report uncovered nodes in the statuses that need code

Bondstone SHALL report a node of a `code-traceable` type that no tag names as
`bondstone/code-coverage`, at the severity the trait's `coverage` sets. With `when`, only
nodes in the listed statuses MUST be reported.

#### Scenario: Planned requirement without code

- Given `code-traceable: {coverage: error, when: [active]}` and an untagged requirement with
  `Status: planned`
- When `bondstone check` runs
- Then no coverage diagnostic is reported for it

### REQ-TRC-005: Warn about tags on retired nodes

Bondstone SHALL report a tag on a node whose status is listed in the trait's `retired` as
`bondstone/tag-retired`.

#### Scenario: Removed requirement still tagged

- Given `retired: [removed]` and a tagged requirement with `Status: removed`
- When `bondstone check` runs
- Then `bondstone/tag-retired` is reported at the tag's line

### REQ-TRC-006: Give items a status of their own

Bondstone SHALL read a line `Status: <status>` as the first text under an item's heading as
the item's status, when the item's type has a lifecycle. Without the line, the item MUST take
the lifecycle's `default` status.

#### Scenario: Item without a status line

- Given a requirement lifecycle with `default: active` and a requirement without a `Status:` line
- When the graph is built
- Then the requirement's status is `active`

### REQ-TRC-007: Let rules ask whether a node is covered

Bondstone SHALL support `covered: true|false` both as a selector key and as a clause, so that
a named rule can require coverage, or select nodes by it.

#### Scenario: Stable command must be implemented

- Given a rule with `when: {type: Command, status: stable}` and `require: [{covered: true}]`
- When a stable command has no tag in code
- Then the rule is reported for that command
