---
id: ADR-001
title: Use Markdown with YAML frontmatter as the document format
status: superseded
owner: dworek
date: '2026-11-10'
---

## Context

Bondstone documents must be pleasant for people to write and review in pull requests,
readable by coding agents without special tooling, and strict enough to validate.

## Decision

Every document is a Markdown file. Metadata and links live in a YAML frontmatter block;
structure (sections, embedded items) comes from Markdown headings.

## Alternatives considered

- Pure YAML/JSON documents: easiest to validate, unpleasant to write prose in.
- A custom markup (like StrictDoc's SDoc): precise, but needs editor support and a learning curve.
- reStructuredText with directives (like Sphinx-Needs): powerful, less familiar than Markdown.

## Consequences

Documents render on GitHub as-is. Validation needs a frontmatter schema per type and
heading conventions for items; anything not expressible that way needs a rule.
