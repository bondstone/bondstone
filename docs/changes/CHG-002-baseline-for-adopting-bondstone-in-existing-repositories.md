---
id: CHG-002
title: Baseline for adopting bondstone in existing repositories
status: accepted
owner: dworek
kind: feature
modifies:
- CAP-diff-checks
decided_by:
- ADR-008
---

## Why

Merging `POC` into `main`, or adopting bondstone in any existing repository, fails `bondstone/status-initial` for every document, because they are all new compared with the target branch. See ADR-008.

## What changes

- `baseline: <commit>` in the profile and a `bondstone baseline [REF]` command that sets it.
- Diff checks compare documents missing at the base with their baseline version.
- A missing baseline commit is reported with a fix hint.
- CI checks out full history.

## Out of scope

Moving the baseline automatically, and baselines per directory.
