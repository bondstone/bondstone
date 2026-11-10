---
id: CAP-scaffolding
title: Document scaffolding
status: draft
owner: dworek
code: SCF
depends_on: [CAP-graph]
constrained_by: [ADR-001]
---

## Purpose

Create and replace documents so that people and agents start from a valid skeleton.

## Requirements

### REQ-SCF-001: Assign the next id

`bondstone new` SHALL assign the next id from the type's `id_format`: the highest existing number plus one, the slug, or values passed with `--set`.

#### Scenario: Next ADR number

- Given ADR-007 is the highest decision
- When `bondstone new adr:Decision --title "Use SQLite"` runs
- Then `ADR-008-use-sqlite.md` is created

### REQ-SCF-002: Pre-fill required frontmatter

`bondstone new` SHALL write the title, every required field, the initial status, the owner and an empty list for each link with a minimum count.

#### Scenario: Defaults

- Given the profile sets `defaults.owner`
- When a decision is scaffolded
- Then it has status proposed, the owner and today's date

### REQ-SCF-003: Mark unfinished content

Templates MUST mark every placeholder with a todo marker so that check reports unfinished documents.

#### Scenario: Fresh document

- Given a scaffolded decision
- When check runs
- Then `bondstone/todo-left` is a warning

### REQ-SCF-004: Supersede documents

`bondstone supersede ID` SHALL create the successor, set the old document to superseded, move incoming links to the successor except from immutable documents, and regenerate views.

#### Scenario: Superseding a decision

- Given CAP-a is constrained by ADR-001
- When `bondstone supersede ADR-001 --title ...` runs
- Then CAP-a is constrained by the new decision

### REQ-SCF-005: Initialise a repository

`bondstone init` SHALL create the profile and generate its views so that a fresh repository checks clean.

#### Scenario: Fresh repository

- Given an empty repository
- When `bondstone init --packs adr@1` runs
- Then `bondstone check` passes
