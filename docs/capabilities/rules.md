---
id: CAP-rules
type: capability:Capability
title: Rules and traits
status: active
owner: dworek
code: RUL
constrained_by: [ADR-003]
depends_on: [CAP-graph, CAP-profiles]
---

## Purpose

A rule selects nodes or files and requires something of them. Packs, bridges and the profile
declare rules; the engine adds its own, named `bondstone/...`. Traits are behaviour a type
opts into, which the engine checks without knowing the method the type belongs to.

## Requirements

### REQ-RUL-001: Select nodes with selectors

Bondstone SHALL match a node against a selector whose keys combine with AND: `type`, `role`,
`trait`, `status`, `covered` and `where: {field: value}`. A list of values means any of them.
A type name without a pack prefix MUST resolve inside the pack that declares the rule or view.

#### Scenario: Role and status

- Given the selector `{role: decision, status: [proposed, accepted]}`
- When it is matched against a rejected `adr:Decision`
- Then the node does not match

### REQ-RUL-002: Evaluate node rules

Bondstone SHALL evaluate a rule with `when` for every node its selector matches and report
each clause of `require` that does not hold: `link` and `incoming` with `min` or `all`,
`field`, `section`, `contains`, `items`, `covered`, `file_field` and `any`.

#### Scenario: Accepted decision without alternatives

- Given a rule that requires accepted decisions to contain a heading "Alternatives considered"
- When an accepted decision lacks it
- Then the rule is reported for that decision, with the rule's description and what is missing

### REQ-RUL-003: Evaluate existence rules

Bondstone SHALL evaluate a rule with `for_each` for every file its glob matches and report the
files whose `document` path, built from the file's path, does not exist or is not a document
of the required type.

#### Scenario: Pack without a README document

- Given a rule `for_each: {glob: "library/*/pack.yaml", document: "{dir}/README.md"}`
- When a pack folder has no `README.md`
- Then the rule is reported for that `pack.yaml`

### REQ-RUL-004: Compare a field with a value in another file

Bondstone SHALL evaluate a `file_field` clause by reading the YAML or JSON file at `path`,
which may use the node's fields as placeholders, and comparing the value at `key` with the
node's field named by `equals`, or with the literal `value`.

#### Scenario: Version drift

- Given a component document with `version: 1.0.0` and a `pack.yaml` that says `1.1.0`
- When a rule compares the two with `file_field`
- Then the rule is reported for the document

### REQ-RUL-005: Keep a catalogue of engine rules

Bondstone SHALL list every `bondstone/...` rule it can emit in one catalogue, with its default
severity, when it fires, why and how to fix it. Every engine rule except `bondstone/profile`
MUST be overridable down to `ignore`.

#### Scenario: Engine rule switched off

- Given the override `bondstone/code-coverage: ignore`
- When `bondstone check` runs
- Then no coverage warning is reported

### REQ-RUL-006: Check the status of nodes with a lifecycle

Bondstone SHALL require a `status` from the lifecycle's `statuses` on every node whose type
has the `lifecycle` trait, and an `owner` on every document whose type has the `owned` trait.

#### Scenario: Unknown status

- Given a decision with `status: done`
- When `bondstone check` runs
- Then `bondstone/field-invalid` is reported at the line of `status`

### REQ-RUL-007: Keep supersession consistent

For a type with the `supersedable` trait, bondstone SHALL report a superseded document whose
status is not `superseded`, a document superseded by more than one document, a cycle of
supersede links, and a document with the status `superseded` that nothing supersedes. When
the lifecycle allows the step, `bondstone/supersede-status` MUST carry the fix command
`bondstone status ID superseded`.

#### Scenario: Superseded but still accepted

- Given ADR-002 with `supersedes: ADR-001`, and ADR-001 with `status: accepted`
- When `bondstone check` runs
- Then `bondstone/supersede-status` is reported for ADR-001

### REQ-RUL-008: Report leftover placeholders

Bondstone SHALL report a `<!-- todo: ... -->` placeholder outside code as
`bondstone/todo-left`: as a warning while the document is in its lifecycle's `initial`
status, and as an error afterwards.

#### Scenario: Placeholder in an accepted decision

- Given an accepted decision that still contains `<!-- todo: alternatives -->`
- When `bondstone check` runs
- Then `bondstone/todo-left` is an error at the line of the placeholder

### REQ-RUL-009: Make every diagnostic actionable

Bondstone SHALL give every diagnostic of a declared rule the rule's id, its description with
what is missing, the node's file and line, and the rule's `hint` and `fix` command. `{id}` in
a hint or a fix command MUST be replaced by the node's id.

#### Scenario: Hint with the node's id

- Given a rule with the hint "Tag the handler with `bondstone: {id}`."
- When it is reported for `CMD-check`
- Then the hint reads "Tag the handler with `bondstone: CMD-check`."
