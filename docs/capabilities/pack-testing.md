---
id: CAP-pack-testing
title: Pack testing
status: draft
owner: dworek
code: PKT
depends_on: [CAP-profiles]
constrained_by: [ADR-003]
---

## Purpose

Let pack and bridge authors test their rules with example repositories.

## Requirements

### REQ-PKT-001: Run fixtures

`bondstone pack test` SHALL run check on every `fixtures/<case>` repository of a pack or bridge and compare the rule ids per severity with `expected.yaml`.

#### Scenario: Unexpected error

- Given a fixture expecting no errors
- When the pack reports one
- Then the case fails and lists the diagnostics

### REQ-PKT-002: Test the local version

The pack or bridge under test SHALL take priority over other sources and the built-in library.

#### Scenario: Editing a built-in pack

- Given a changed copy of adr in its source folder
- When its fixtures run
- Then the changed copy is used
