---
id: ADR-002
title: Allow AsciiDoc documents alongside Markdown
status: accepted
owner: dworek
date: '2026-11-10'
supersedes: ADR-001
---

## Context

Some teams keep architecture docs in AsciiDoc and do not want to convert them.

## Decision

Accept `.adoc` files with the same YAML frontmatter; headings use AsciiDoc `==` syntax.

## Alternatives considered

- Markdown only (ADR-001): forces conversion.

## Consequences

The parser needs a second heading syntax; views stay Markdown.
