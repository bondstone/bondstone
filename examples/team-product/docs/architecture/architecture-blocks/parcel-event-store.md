---
id: ABB-parcel-event-store
title: Parcel event store
status: approved
owner: tracking-team
layer: data
satisfies: [AREQ-003]
constrained_by: [ADR-001]
---
## Responsibility

Collect scans from carriers within their rate limits and keep them as an ordered,
append-only history per parcel.

## Interfaces

- Offers: the events of a parcel in order, and a feed of new events.
- Needs: carrier scan feeds.
