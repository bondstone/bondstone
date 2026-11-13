---
id: CAP-views
type: capability:Capability
title: Generated views
status: active
owner: Adam Dworzyński
code: VIE
depends_on: [CAP-graph, CAP-rules]
constrained_by: [ADR-010]
---

## Purpose

Indexes and traceability overviews are generated from the graph and committed, so readers get
them without running a tool. Nobody edits them by hand, and `check` fails when one no longer
matches the documents it was generated from.

## Requirements

### REQ-VIE-001: Render table views

Bondstone SHALL render a view with `render: table` as a Markdown table with one row for every
node its `select` matches and one column for every entry of `columns`: `id`, `status`,
`parent` or a field. The id MUST link to the node's document, relative to the view's file.
Rows are ordered by the `sort` keys, by id otherwise, and numbers inside ids order
numerically.

#### Scenario: Decision log

- Given a view with `select: {type: Decision}` and `columns: [id, title, status]`
- When `bondstone gen` runs
- Then the file lists every decision, with ADR-2 before ADR-10

### REQ-VIE-002: Render tree views

Bondstone SHALL render a view with `render: tree` as a nested list: the nodes that `select`
matches, and under each node the nodes reached by the next entry of `levels`, which is
`{link: L}` for outgoing links or `{incoming: L}` for incoming ones.

#### Scenario: From outcomes to solutions

- Given a view with `select: {type: Outcome}` and `levels: [{incoming: serves}, {incoming: addresses}]`
- When `bondstone gen` runs
- Then each outcome lists its opportunities, and each opportunity its solutions

### REQ-VIE-003: Write only the views that changed

`bondstone gen` SHALL write every view whose file is missing or differs from the rendered
content, print the paths it wrote, and write nothing when every view is up to date.

#### Scenario: Running gen twice

- Given a repository whose views are stale
- When `bondstone gen` runs twice
- Then the second run prints "views are up to date" and changes no file

### REQ-VIE-004: Fail the check on a stale view

`bondstone check` SHALL report a view whose file is missing or differs from what `gen` would
write as `bondstone/view-stale`, with the fix command `bondstone gen`.

#### Scenario: Document added without regenerating

- Given a new decision and a decision log that was not regenerated
- When `bondstone check --format json` runs
- Then the `bondstone/view-stale` diagnostic carries `fix: {command: [bondstone, gen]}`

### REQ-VIE-005: Mark generated files

Bondstone SHALL start every generated view with a comment that names the view and says not to
edit it. A view's output file MUST NOT be read as a document, even inside the profile's `docs`
globs.

#### Scenario: Views inside the docs folder

- Given `docs: ["docs/**/*.md"]` and a view written to `docs/generated/decisions.md`
- When `bondstone check` runs
- Then no `bondstone/untyped-document` is reported for the view

### REQ-VIE-006: Show linked nodes in table columns

Bondstone SHALL render a table column that names a link as the ids of the linked nodes, each
a Markdown link to its document: the name of a link for the nodes a row points at, in the
order the document lists them, and `<-name` for the nodes that point at the row, sorted by
id. The heading reads the link's name as words, with an arrow for `<-name`. A target that
does not exist is shown as plain text, and a `<-name` column for an unknown link MUST be a
configuration error.

#### Scenario: Where a decision applies

- Given a table of decisions with the column `<-constrained_by`, and CAP-a and CAP-b constrained by ADR-002
- When the view is rendered
- Then the row of ADR-002 has the cell `[CAP-a](...), [CAP-b](...)` under the heading `← Constrained by`

### REQ-VIE-007: Render matrix views

Bondstone SHALL render a view with `render: matrix` as one row per node matching `rows` and
one column per node matching `cols`, both sorted by id, with a mark in every cell whose row
is connected to its column by the links under `via`. `via` is a path: each entry is followed
from the nodes the previous one reached, along the link or against it for `<-name`. A matrix
without `rows`, `cols` or `via`, one of those keys on another layout, and an unknown link
under `via` MUST be configuration errors.

#### Scenario: Capabilities against decisions

- Given `rows: {type: capability:Capability}`, `cols: {type: adr:Decision}` and `via: [constrained_by]`
- When CAP-a is constrained by ADR-002
- Then the cell of CAP-a and ADR-002 has a mark and the other cells of that row are empty

#### Scenario: A path of two links

- Given rows of decisions, columns of capabilities and `via: ["<-constrained_by", "<-depends_on"]`
- When CAP-a is constrained by ADR-002 and CAP-b depends on CAP-a
- Then the cell of ADR-002 and CAP-b has a mark
