---
{id: ADR-006, title: Generated views are committed and checked for staleness, status: proposed,
  owner: dworek, date: '2026-11-10'}
---

## Context

Indexes such as a decision log or a changelog drift as soon as they are maintained by hand.

## Decision

Views are generated Markdown files committed to the repository. `bondstone gen` writes them and `bondstone check` fails when one is out of date.

## Alternatives considered

- Generate views only in a docs site build: always fresh, but invisible in the repository and in reviews.

## Consequences

Views are readable on GitHub and reviewable in diffs. Every document change needs a `bondstone gen` before committing.
