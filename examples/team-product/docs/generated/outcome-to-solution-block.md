<!-- bondstone:generated view=ost-togaf-lite/outcome-to-solution-block; do not edit, run `bondstone gen` -->
# From outcomes to solution blocks

- [OUT-1](../discovery/outcomes/OUT-1-fewer-where-is-my-parcel-contacts.md) Fewer "where is my parcel" contacts _(active)_
  - [OPP-1](../discovery/opportunities/OPP-1-i-cannot-tell-when-my-parcel-will-arrive.md) I cannot tell when my parcel will arrive _(pursuing)_
    - [SOL-1](../discovery/solutions/SOL-1-live-arrival-estimate-on-the-tracking-page.md) Live arrival estimate on the tracking page _(committed)_
      - [AREQ-001](../architecture/requirements/AREQ-001-show-an-arrival-window-on-the-tracking-page.md) Show an arrival window on the tracking page _(satisfied)_
        - [ABB-arrival-estimation](../architecture/architecture-blocks/arrival-estimation.md) Arrival estimation _(approved)_
          - [SBB-eta-service](../architecture/solution-blocks/eta-service.md) ETA service _(live)_
      - [AREQ-002](../architecture/requirements/AREQ-002-arrival-windows-are-at-most-five-minutes-stale.md) Arrival windows are at most five minutes stale _(approved)_
        - [ABB-arrival-estimation](../architecture/architecture-blocks/arrival-estimation.md) Arrival estimation _(approved)_
          - [SBB-eta-service](../architecture/solution-blocks/eta-service.md) ETA service _(live)_
  - [OPP-2](../discovery/opportunities/OPP-2-i-miss-the-courier-because-nobody-told-me-they-were-close.md) I miss the courier because nobody told me they were close _(open)_
    - [SOL-2](../discovery/solutions/SOL-2-text-message-when-the-courier-is-ten-stops-away.md) Text message when the courier is ten stops away _(idea)_
