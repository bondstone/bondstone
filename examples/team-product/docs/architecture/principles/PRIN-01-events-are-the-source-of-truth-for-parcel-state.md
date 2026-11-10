---
id: PRIN-01
title: Events are the source of truth for parcel state
status: approved
owner: tracking-team
---
## Statement

The state of a parcel is always derived from recorded events and never stored on its own.

## Rationale

Carriers correct scans after the fact. A derived state can be recomputed; a stored state
silently keeps the mistake.

## Implications

- No component updates parcel state directly.
- Every projection can be rebuilt from the event store.
