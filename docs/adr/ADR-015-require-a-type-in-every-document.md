---
id: ADR-015
type: adr:Decision
title: Require a type in every document's frontmatter
status: accepted
owner: dworek
date: 2026-11-10
---

## Context

[The design](../design.md) says a document's type comes from the path it lives at. During
phase 1 the maintainer asked for the type to be written in the document as well: bondstone
should later become compliant with OKF, and a document that states its own type helps with
that. A reader or a tool can then tell what a document is without knowing the folder layout
of the repository.

## Decision

Every document declares `type: <pack>:<Type>` in its frontmatter, with the qualified name.
The path must still match: a document whose declared type lives elsewhere is
`bondstone/type-mismatch`. A document at a type's path without the key is
`bondstone/type-missing` and is still checked as the type its path implies. A file under the
profile's `docs` globs at no type's path is `bondstone/untyped-document`.

## Alternatives considered

- **Type from the path only**, as the design says. Less to write, but the document does not
  describe itself.
- **Type from the frontmatter only.** Documents could live anywhere, and a missing or
  mistyped key would silently remove a file from every check.

## Consequences

- One more frontmatter line per document; scaffolding will write it.
- Two types may share a folder, because the key tells them apart.
- Documents written for the POC need the key added. The error names the type to add.
