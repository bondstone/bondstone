---
{id: ADR-001, title: Use Markdown with YAML frontmatter as the document format, status: proposed,
  owner: dworek, date: '2026-11-10'}
---

## Context

Documents must be pleasant to write and review in pull requests, readable by coding agents without special tooling, and strict enough to validate.

## Decision

Every document is a Markdown file. Metadata and links live in YAML frontmatter; structure (sections, embedded items) comes from Markdown headings.

## Alternatives considered

- Pure YAML or JSON documents: easy to validate, unpleasant for prose.
- A custom markup such as StrictDoc's SDoc: precise, but needs editor support.
- reStructuredText with directives (Sphinx-Needs): powerful, less familiar than Markdown.

## Consequences

Documents render on GitHub as they are. Validation needs a frontmatter schema per type and heading conventions for items; anything else needs a rule.
