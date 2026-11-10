---
id: ADR-001
title: Store carrier scans as events in Postgres
status: accepted
owner: tracking-team
date: 2026-09-14
---
## Context

Parcel state is derived from scans sent by four carriers, each with its own format and
delays. Corrections arrive hours after the original scan.

## Decision

Every scan is stored as an immutable event in a Postgres table partitioned by day. Parcel
state is a projection over those events.

## Alternatives considered

- **Update a parcel row in place.** Simpler, but late corrections overwrite history and
  estimates cannot be recomputed.
- **Kafka as the system of record.** Fits the model, but the team does not operate Kafka
  and volume is under 200 events per second.

## Consequences

Projections must tolerate out-of-order events. Storage grows by about 4 GB a month, and
partitions older than 18 months are archived.
