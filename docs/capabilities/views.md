---
id: CAP-views
title: Generated views
status: draft
owner: dworek
code: VIE
depends_on: [CAP-graph]
constrained_by: [ADR-006]
---

## Purpose

Generate Markdown indexes from the graph and keep them in sync.

## Requirements

### REQ-VIE-001: Render tables

Bondstone SHALL render `table` views of the selected nodes, sorted naturally by id, with linked ids and the configured columns.

#### Scenario: Decision log

- Given three decisions
- When `bondstone gen` runs
- Then the log lists ADR-001 to ADR-003 with links

### REQ-VIE-002: Render trees

Bondstone SHALL render `tree` views that walk the configured incoming or outgoing links level by level from the selected root nodes.

#### Scenario: Changelog

- Given a release that includes a proposal
- When `bondstone gen` runs
- Then the proposal is nested under the release

### REQ-VIE-003: Report stale views

Bondstone SHALL report every view whose committed file differs from what would be generated.

#### Scenario: Forgotten gen

- Given a new decision
- When check runs without `bondstone gen`
- Then `bondstone/view-stale` is reported

### REQ-VIE-004: Write only changed views

`bondstone gen` SHALL write a view only when its content changes and SHALL exclude generated files from the graph.

#### Scenario: Nothing changed

- Given views are up to date
- When `bondstone gen` runs
- Then no file is written
