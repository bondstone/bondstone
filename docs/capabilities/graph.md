---
id: CAP-graph
title: Document graph
status: draft
owner: dworek
code: GRA
constrained_by: [ADR-001]
---

## Purpose

Turn the repository's Markdown documents into a graph of typed nodes and links.

## Requirements

### REQ-GRA-001: Determine document types

Bondstone SHALL type a document by the `paths` globs of its type or by an explicit `type:` key, and SHALL report conflicting or ambiguous types.

#### Scenario: Explicit type

- Given a file in a scanned folder with `type: adr:Decision`
- When the graph is built
- Then the file is an adr:Decision node

### REQ-GRA-002: Reject unknown frontmatter keys

Bondstone SHALL report every frontmatter key that is neither a declared field, a trait key nor a link of the document's type.

#### Scenario: Typo in a link name

- Given a decision with `supersede: ADR-001`
- When check runs
- Then `bondstone/field-unknown` lists the allowed fields and links

### REQ-GRA-003: Extract embedded items

Bondstone SHALL turn headings that match a type's item pattern into child nodes linked to their document, and SHALL report non-matching headings in the item section.

#### Scenario: Requirement headings

- Given a capability with `### REQ-AA-001: Thing`
- When the graph is built
- Then REQ-AA-001 is a node whose parent is the capability

### REQ-GRA-004: Resolve links by name

Bondstone SHALL map a frontmatter key to the link of that name available for the document's type, and SHALL require the qualified name when the short name is ambiguous.

#### Scenario: Bridge link

- Given bridge adr-capability defines constrained_by
- When a capability has `constrained_by: [ADR-001]`
- Then the node links to ADR-001

### REQ-GRA-005: Validate link targets

Bondstone SHALL report links to missing documents, to documents of the wrong type, and links below a link type's minimum or above its maximum count.

#### Scenario: Broken link

- Given a solution with `addresses: [OPP-9]`
- When OPP-9 does not exist
- Then `bondstone/link-broken` is reported

### REQ-GRA-006: Enforce unique and well-formed ids

Bondstone SHALL report missing ids, ids that do not match the type's `id_pattern`, and ids used twice.

#### Scenario: Duplicate id

- Given two documents with id ADR-001
- When check runs
- Then `bondstone/id-duplicate` points at the first one
