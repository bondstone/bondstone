---
id: ADR-002
title: Estimate arrival from route history inside the ETA service
status: accepted
owner: tracking-team
date: 2026-10-06
---
## Context

The arrival window must be recomputed whenever a new scan arrives and must be available
to the tracking page within seconds.

## Decision

The ETA service computes windows itself from per-route historical percentiles that are
refreshed nightly. It does not call carrier systems when a customer opens the page.

## Alternatives considered

- **Ask each carrier's ETA endpoint on page load.** Only two of four carriers offer one,
  and both rate-limit below peak traffic.
- **A trained model behind a separate inference service.** More accurate in tests, but it
  adds a deployment and an on-call rota for a 3-point gain.

## Consequences

Accuracy depends on route history, so new routes start with wide windows. The nightly
refresh becomes a job the team must monitor.
