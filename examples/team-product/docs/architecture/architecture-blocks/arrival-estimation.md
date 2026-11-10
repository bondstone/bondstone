---
id: ABB-arrival-estimation
title: Arrival estimation
status: approved
owner: tracking-team
layer: application
satisfies: [AREQ-001, AREQ-002]
constrained_by: [ADR-002]
---
## Responsibility

Turn the events known for a parcel into an arrival window, and keep that window current
as new events arrive.

## Interfaces

- Offers: the current window for a parcel.
- Needs: the ordered events of a parcel and historical travel times per route.
