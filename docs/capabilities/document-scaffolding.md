---
id: CAP-document-scaffolding
title: Document scaffolding
status: active
owner: dworek
code: SCF
constrained_by: [ADR-002]
---

## Purpose

`bondstone new` creates documents that already satisfy their type's structure, so people
and agents start from a valid skeleton instead of writing frontmatter by hand.

## Requirements

### REQ-SCF-001: Assign the next id

`bondstone new` SHALL assign the next free id from the type's `id_format`: the highest
existing number plus one, or a slug (also used in the filename) for slug-based formats.

#### Scenario: Next ADR number

- Given ADR-007 is the highest existing decision
- When `bondstone new adr:Decision --title "Use SQLite"` runs
- Then `docs/adr/ADR-008-use-sqlite.md` is created with `id: ADR-008`

### REQ-SCF-002: Pre-fill required frontmatter

`bondstone new` SHALL write every required field, the initial lifecycle status, the owner
and an empty list for each link with a minimum count.

#### Scenario: Defaults

- Given the profile sets `defaults.owner: dworek`
- When a decision is scaffolded
- Then it has `status: proposed`, `owner: dworek` and today's `date`

### REQ-SCF-003: Mark unfinished content

Templates MUST mark every placeholder with `<!-- todo: ... -->`, so `bondstone check`
reports unfinished documents.

#### Scenario: Placeholder left in an accepted decision

- Given a scaffolded decision whose status was changed to `accepted`
- When the placeholders were not replaced
- Then `bondstone check` reports `bondstone/todo-left` as an error
