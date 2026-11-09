---
id: ADR-003
title: Schedule reminders with local notifications
status: accepted
owner: dawid
date: 2026-10-20
---
## Context

Reminders must work offline and without a backend.

## Decision

Schedule reminders as local notifications on the device.

## Alternatives considered

- Push notifications from a server: needs a backend and accounts.

## Consequences

Reminder times are recalculated on the device after each completion.
