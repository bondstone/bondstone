---
id: CHG-005
title: File-field and for-each rules
status: accepted
owner: dworek
kind: feature
modifies:
- CAP-rules
---

## Why

Some facts live outside Markdown documents: a pack's version is in `pack.yaml`, and every manifest should have a README. Rules can't express either today (engine features 1 and 2 in `docs/self-hosting.md`).

## What changes

- A `file_field` clause: a value in a YAML/JSON file next to the document must equal a document field or a literal.
- `for_each` rules: every file matching a glob has a document of a given type at a templated path.

## Out of scope

TOML files, and comparing values across repositories.
