---
id: SBB-parcel-events
title: Parcel events
status: live
owner: tracking-team
technology: Python 3.13, Postgres 17
realizes: [ABB-parcel-event-store]
---
## Responsibility

Polls carrier scan feeds, stores every scan as an immutable event and publishes new events.

## Interfaces

- `GET /parcels/{id}/events` returns the events of a parcel in order.
- Publishes new events through Postgres `LISTEN/NOTIFY`.

## Operations

One poller per carrier, each with a token bucket set to 80% of the contracted rate.
