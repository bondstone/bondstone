---
id: CAP-code-traceability
title: Code traceability
status: active
owner: dworek
code: TRC
depends_on: [CAP-graph]
constrained_by: [ADR-005]
---

## Purpose

Connect code to the documents it implements with tags in comments.

## Requirements

### REQ-TRC-001: Recognise tags

Bondstone SHALL read `bondstone: ID[, ID…]` tags, with whitespace after the colon and complete ids (starting with an uppercase letter, not ending with a hyphen, and not followed by more id characters), from the files in `code.include` minus `code.exclude`.

#### Scenario: String literal is not a tag

- Given code containing `"bondstone:part_of"`
- When check runs
- Then no tag is read

#### Scenario: Placeholder in a hint

- Given a manifest hint mentioning `bondstone: REQ-...`
- When check runs
- Then no tag is read

### REQ-TRC-002: Reject wrong references

Bondstone SHALL report tags for unknown ids and for nodes whose type is not code-traceable.

#### Scenario: Tag on a decision

- Given a tag `bondstone: ADR-001`
- When check runs
- Then `bondstone/code-ref-not-traceable` is reported

### REQ-TRC-003: Report coverage

Bondstone SHALL report code-traceable nodes without a tag at the severity set by the trait's `coverage`.

#### Scenario: Untagged requirement

- Given REQ-AA-001 with coverage warn and no tag
- When check runs
- Then `bondstone/code-coverage` is a warning
