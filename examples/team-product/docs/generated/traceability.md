<!-- bondstone:generated view=togaf-lite/traceability; do not edit, run `bondstone gen` -->
# Requirements traceability

Each requirement, the architecture blocks that satisfy it, and the solution blocks that realize them.

- [AREQ-001](../architecture/requirements/AREQ-001-show-an-arrival-window-on-the-tracking-page.md) Show an arrival window on the tracking page _(satisfied)_
  - [ABB-arrival-estimation](../architecture/architecture-blocks/arrival-estimation.md) Arrival estimation _(approved)_
    - [SBB-eta-service](../architecture/solution-blocks/eta-service.md) ETA service _(live)_
- [AREQ-002](../architecture/requirements/AREQ-002-arrival-windows-are-at-most-five-minutes-stale.md) Arrival windows are at most five minutes stale _(approved)_
  - [ABB-arrival-estimation](../architecture/architecture-blocks/arrival-estimation.md) Arrival estimation _(approved)_
    - [SBB-eta-service](../architecture/solution-blocks/eta-service.md) ETA service _(live)_
- [AREQ-003](../architecture/requirements/AREQ-003-carrier-calls-stay-within-contracted-rate-limits.md) Carrier calls stay within contracted rate limits _(approved)_
  - [ABB-parcel-event-store](../architecture/architecture-blocks/parcel-event-store.md) Parcel event store _(approved)_
    - [SBB-parcel-events](../architecture/solution-blocks/parcel-events.md) Parcel events _(live)_
