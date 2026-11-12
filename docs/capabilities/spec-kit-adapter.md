---
id: CAP-spec-kit-adapter
type: capability:Capability
title: Spec Kit adapter
status: draft
owner: Adam Dworzyński
code: SKT
depends_on: [CAP-graph, CAP-rules, CAP-diff-checks, CAP-profiles]
constrained_by: [ADR-007, ADR-013, ADR-017]
---

## Purpose

Spec Kit plans one change at a time in a folder under `specs/`. The adapter in the library
makes those folders part of the graph, so that rules can ask of every finished feature that
it was folded into the living capability specs and rests on accepted decisions. It consists
of the `speckit` pack, the bridges `speckit-capability` and `speckit-adr`, the preset
`starter-speckit` and a Spec Kit preset for the frontmatter.

## Requirements

### REQ-SKT-001: Read a Spec Kit feature folder as one node

The `speckit` pack SHALL define the type `speckit:Feature` for `specs/<id>/spec.md`, whose id
is the folder's name in the form `NNN-name`. Its status MUST be derived from the folder:
`implemented` when every task in `tasks.md` is ticked, else `planned` when `plan.md` exists,
else `specified`. `plan.md` and `tasks.md` are not documents.

#### Scenario: A feature with one open task

- Given `specs/002-logout/` with `spec.md`, `plan.md` and a `tasks.md` with one unticked task
- When `bondstone check` runs
- Then `002-logout` is a `speckit:Feature` in status `planned`

### REQ-SKT-002: Add the frontmatter through a Spec Kit preset

The library SHALL ship a Spec Kit preset that prepends a frontmatter block with `id`,
`type: speckit:Feature`, `title` and the links `modifies`, `delivers` and `decided_by` to
Spec Kit's `spec-template`, and that tells the agent in the `speckit.specify` command how to
fill it in. The preset MUST state the Spec Kit versions it accepts, starting at the release it
was tested with.

#### Scenario: A new feature

- Given a Spec Kit 1.4.0 project with the preset installed
- When Spec Kit's `create-new-feature` script creates `specs/001-snooze-reminders/spec.md`
- Then the file starts with the frontmatter block, before the template's title

### REQ-SKT-003: Fold an implemented feature into the capabilities

The bridge `speckit-capability` SHALL let a feature name the capabilities it `modifies` and
the requirements it `delivers`. An implemented feature MUST deliver only requirements that
are active and tagged in code, and it is warned about when it names neither a capability nor
a requirement.

#### Scenario: The last task is ticked too early

- Given a feature that delivers REQ-AA-002, which still has `Status: planned` and no tag in code
- When the last task in its `tasks.md` is ticked
- Then `speckit-capability/implemented-feature-delivers-covered-requirements` is an error

### REQ-SKT-004: Rest an implemented feature on accepted decisions

The bridge `speckit-adr` SHALL let a feature name the decisions it is `decided_by`, and an
implemented feature MUST name only accepted decisions.

#### Scenario: A decision still proposed

- Given an implemented feature with `decided_by: [ADR-002]` and ADR-002 in status `proposed`
- When `bondstone check` runs
- Then `speckit-adr/implemented-feature-rests-on-accepted-decisions` is an error

### REQ-SKT-005: Ask for a feature when code changes

The preset `starter-speckit` SHALL extend `starter` with the `speckit` pack and its two
bridges, and with a diff rule that a change to the repository's code comes with a changed
feature: its `spec.md`, `plan.md` or `tasks.md`. The rule is a warning by default and MUST be
exemptible with a `Spec-Impact` commit trailer.

#### Scenario: Code without a feature

- Given a profile that extends `starter-speckit` and raises the rule to `error`
- When a pull request changes source files and nothing under `specs/`
- Then `starter-speckit/source-change-has-feature` fails the check
