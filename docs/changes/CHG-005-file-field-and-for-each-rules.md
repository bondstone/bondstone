---
id: CHG-005
title: File-field and for-each rules
status: accepted
owner: dworek
kind: feature
modifies:
- CAP-rules
- CAP-profiles
- CAP-diff-checks
---

## Why

Some facts live outside Markdown documents: a pack's version is in `pack.yaml`, and every manifest should have a README. Rules can't express either today (engine features 1 and 2 in `docs/self-hosting.md`).

## What changes

- A `file_field` clause: a value in a YAML/JSON file next to the document must equal a document field or a literal.
- `for_each` rules: every file matching a glob has a document of a given type at a templated path.
- `profile check` validates `for_each` rules (REQ-PRF-007 makes rule validation explicit).
- An `exists` clause for diff rules, so code changes can require an accepted proposal without touching it (found while implementing: the implementation push changes no proposal).

## Out of scope

TOML files, and comparing values across repositories.
