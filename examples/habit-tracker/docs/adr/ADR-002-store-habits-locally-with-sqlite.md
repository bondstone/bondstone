---
id: ADR-002
type: adr:Decision
title: Store habits locally with SQLite
status: accepted
owner: dawid
date: 2026-10-12
supersedes: ADR-001
---
## Context

Users want to log habits offline and without creating an account.

## Decision

Store habits and completions in an on-device SQLite database.

## Alternatives considered

- Firebase (ADR-001): needs an account and a connection.
- Hive: less suitable for the reporting queries we need.

## Consequences

No sync between devices until we add an export or sync feature.
