---
id: ADR-016
type: adr:Decision
title: Keep the engine rule catalogue in code
status: proposed
owner: Adam Dworzyński
date: 2026-11-12
---

## Context

[The design](../design.md) gives bondstone a local `diagnostics` pack: one document lists every
engine rule as an item, each item is tagged where the engine emits the rule, and
`bondstone explain` reads that document.

Two things stand in the way. `explain` must work after `pip install bondstone`, so the document
would have to ship inside the package. And the engine needs each rule's default severity at
run time, so the severity would live in code and the explanation in Markdown: two sources for
one catalogue.

## Decision

The catalogue of engine rules is code: `catalogue.py` holds every `bondstone/...` rule with its
default severity, when it fires, why, and the fix. `bondstone rules` and `bondstone explain`
read it. There is no `diagnostics` pack.

A test keeps the catalogue complete: every rule id that the engine's source emits is in the
catalogue, and every entry is emitted somewhere.

## Alternatives considered

- **The document is the source**, as the design says. It would exercise items and tags on
  42 nodes and make the catalogue readable on GitHub, but it needs Markdown as package data
  and leaves the severities in code.
- **Code is the source and the document is generated from it.** The rules would be nodes that
  other documents can link to. It needs a generator outside the view system that only
  bondstone uses, and a generated file that is also read as a document, which the engine
  otherwise forbids.

## Consequences

- One source, no data files in the package, and `explain` works offline.
- Engine rules are not nodes, so a capability cannot link to the rules it emits, and no view
  lists them. `bondstone rules` is the list.
- The design notes that some facts are better checked by tests than by documentation rules.
  This is one of them.
- If linking to engine rules becomes useful, the generated-document alternative can be added
  without changing the source.
