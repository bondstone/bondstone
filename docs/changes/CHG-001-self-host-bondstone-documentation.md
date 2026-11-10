---
id: CHG-001
title: Self-host bondstone documentation (phase 1)
kind: docs
status: accepted
owner: dworek
decided_by: [ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007]
---

## Why

Bondstone should be documented with bondstone, both to keep its own documentation alive and to find what the engine is missing. See `docs/self-hosting.md`.

## What changes

- Profile with the `adr`, `capability`, `change` and `release` packs and four bridges.
- Local packs `change` and `release` and bridges `change-capability`, `change-adr` and `release-change`, with fixtures.
- Seven decisions backfilled from `docs/design.md`.
- Nine capability specs describing current behaviour, with code tags.
- `id_format` accepts values passed with `--set` (needed for `v{version}`).

## Out of scope

The `cli`, `library` and `engine` packs and the engine features they need (phases 2 and 3).
