---
id: SBB-eta-service
title: ETA service
status: live
owner: tracking-team
technology: Python 3.13, FastAPI
realizes: [ABB-arrival-estimation]
depends_on: [SBB-parcel-events]
constrained_by: [ADR-002]
---
## Responsibility

Computes a two-hour arrival window per parcel from route history and recomputes it when a
new event arrives.

## Interfaces

- `GET /parcels/{id}/eta` returns the current window.
- Consumes the new-event feed of `SBB-parcel-events`.

## Operations

Runs as two replicas. Route percentiles are refreshed by a nightly job; the service keeps
serving the previous percentiles if the job fails.
