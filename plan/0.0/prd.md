---
type: prd
id: PRD-0.0
title: Bootstrap
description: The Spec Kit extension and preset with the stopgap behind them, running the simple-app workflow.
status: draft
version: V-0.0
---

# PRD-0.0 Bootstrap

## Why

Test the riskiest assumption first: that agents follow the flow when Bondstone names one next step, keep living docs current in the same commit, and name tests after example IDs. The roadmap's V-0.0 entry holds the scope and no-gos.

## Goals and metrics

- `next` names the right step in at least 9 of 10 logged sessions.
- Bondstone's own repository passes `check` with no errors.
- The pre-commit check finishes in under 1 s.

## Deltas

- ADDED: PROFILE-1, PROFILE-2, PROFILE-3, PROFILE-4, PROFILE-5, PROFILE-6, PROFILE-7, PROFILE-8, PROFILE-9
- ADDED: SPECKIT-1, SPECKIT-2, SPECKIT-3, SPECKIT-4, SPECKIT-5, SPECKIT-6, SPECKIT-7, SPECKIT-8, SPECKIT-9, SPECKIT-10, SPECKIT-11, SPECKIT-12, SPECKIT-13

## Stories

The proof of concept on the `poc` branch built these stories directly, without Spec Kit folders; they are listed so the table is complete.

| ID | Title | Proves | Depends on | Status |
| --- | --- | --- | --- | --- |
| ST-1 | Read living and change docs | PROFILE-1, PROFILE-2, PROFILE-3, PROFILE-4 | — | |
| ST-2 | Evidence from test names | PROFILE-5 | ST-1 | |
| ST-3 | Deltas and stories | PROFILE-6, PROFILE-7, PROFILE-8 | ST-1 | |
| ST-4 | Phases | PROFILE-9 | ST-3 | |
| ST-5 | Stories as Spec Kit folders | SPECKIT-4, SPECKIT-5, SPECKIT-6 | ST-3 | |
| ST-6 | check, status and next | SPECKIT-7, SPECKIT-8, SPECKIT-9 | ST-4, ST-5 | |
| ST-7 | Extension, wrapper, commands and templates | SPECKIT-1, SPECKIT-2, SPECKIT-3, SPECKIT-13 | ST-6 | |
| ST-8 | Preset | SPECKIT-11 | ST-7 | |
| ST-9 | Pre-commit hook | SPECKIT-10 | ST-6 | |
| ST-10 | Agent follows next | SPECKIT-12 | ST-7, ST-8 | |
