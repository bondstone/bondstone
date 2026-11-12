---
id: CAP-graph
type: capability:Capability
title: Documents, items and links
status: active
owner: Adam Dworzyński
code: GRA
constrained_by: [ADR-008, ADR-015]
depends_on: [CAP-profiles]
---

## Purpose

Bondstone reads a repository's Markdown documents into one typed graph: a node for every
document and every item, and an edge for every link. Every other check works on that graph,
so a document that cannot be loaded into it is an error, not something to skip.

## Requirements

### REQ-GRA-001: Read Markdown with YAML frontmatter

Bondstone SHALL read a document as a YAML mapping between a first line `---` and the next
`---`, followed by a Markdown body, and remember the line of every frontmatter key and every
heading. Headings inside fenced code MUST NOT count. A file that is not UTF-8, or whose
frontmatter is not closed, not valid YAML or not a mapping, MUST be reported as
`bondstone/parse-error`.

#### Scenario: Frontmatter that is not closed

- Given a document that starts with `---` and has no closing `---`
- When `bondstone check` runs
- Then `bondstone/parse-error` is reported for that file

### REQ-GRA-002: Derive the id pattern and the path glob from templates

Bondstone SHALL derive the pattern that a type's ids must match from the type's `id` template,
and the glob that finds its documents from its `path` template. `{n:03d}` MUST match a number
of at least three digits, and the placeholders of one path segment MUST collapse to one `*`.

#### Scenario: ADR templates

- Given a type with `id: "ADR-{n:03d}"` and `path: "docs/adr/{id}-{slug}.md"`
- When the configuration is loaded
- Then ids must match `^ADR-\d{3,}$` and documents are found with `docs/adr/*.md`

### REQ-GRA-003: Require every document to state its type

Bondstone SHALL load a document as the type its frontmatter key `type` names, with the
qualified name, and only when the file is at that type's path. A missing key MUST be reported
as `bondstone/type-missing` and the document still checked as the type its path implies. An
unknown type, a type whose path does not match, and an embedded type MUST be errors.

#### Scenario: Missing type

- Given a file at `docs/adr/ADR-001-a.md` without `type`
- When `bondstone check` runs
- Then `bondstone/type-missing` suggests `type: adr:Decision`, and the document's other
  checks still run

### REQ-GRA-004: Treat the docs globs as managed folders

Bondstone SHALL report a file that matches the profile's `docs` globs but is at no type's
path as `bondstone/untyped-document`. Generated views MUST NOT be read as documents.

#### Scenario: Loose notes

- Given `docs: ["docs/**/*.md"]` and a file `docs/notes.md` that no type's path matches
- When `bondstone check` runs
- Then `bondstone/untyped-document` is reported for `docs/notes.md`

### REQ-GRA-005: Turn item headings into nodes

Bondstone SHALL create a node for every heading that matches the item heading of the
document's type, inside the type's item section when it names one. The item's body runs to
the next heading of the same or a higher level. A heading at the item level that does not
match MUST be reported as `bondstone/item-heading`.

#### Scenario: Requirement in a capability

- Given a capability with `### REQ-REM-001: Remind at the usual time` under `## Requirements`
- When the graph is built
- Then `REQ-REM-001` is a node of type `capability:Requirement` whose document is the capability

### REQ-GRA-006: Read links from frontmatter

Bondstone SHALL read a frontmatter key that names a link starting at the document's type as
a list of target ids, and index every link by its target, so that rules and views can follow
links in both directions. A key that matches links of several packs MUST be reported as
`bondstone/link-ambiguous`.

#### Scenario: Incoming links

- Given a capability with `constrained_by: [ADR-001]`
- When a rule asks for the incoming `constrained_by` links of ADR-001
- Then it finds the capability

### REQ-GRA-007: Check that ids are present, well formed and unique

Bondstone SHALL report a document without `id`, an id that does not match its type's
pattern, and an id used twice. An item's id MUST carry its own document's value for a
placeholder that names a field, such as `{code}`.

#### Scenario: Requirement with another capability's code

- Given a capability with `code: HAB` and an item `REQ-REM-001`
- When `bondstone check` runs
- Then `bondstone/id-format` is reported for the item

### REQ-GRA-008: Check fields and sections against the type

Bondstone SHALL validate a document's frontmatter fields against the type's JSON Schema and
report missing required fields, and unknown keys and invalid values at the line of the key.
It SHALL report every section the type requires and the document lacks.

#### Scenario: Unknown key

- Given a decision with the key `colour`, which is neither a field nor a link of its type
- When `bondstone check` runs
- Then `bondstone/field-unknown` is reported at the line of `colour`

### REQ-GRA-009: Check links against their definition

Bondstone SHALL report a link whose target does not exist, whose target has a type the link
does not allow, that points at its own document, or whose number of targets is below the
link's `min` or above its `max`.

#### Scenario: Broken link

- Given a solution with `addresses: [OPP-9]` and no node `OPP-9`
- When `bondstone check` runs
- Then `bondstone/link-broken` is reported at the line of `addresses`
