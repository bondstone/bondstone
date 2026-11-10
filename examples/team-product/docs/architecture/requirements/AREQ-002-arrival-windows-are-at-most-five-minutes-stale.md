---
id: AREQ-002
title: Arrival windows are at most five minutes stale
status: approved
owner: tracking-team
kind: quality
priority: must
motivated_by: [PRIN-01, PRIN-02]
---
## Statement

The arrival window shown to a customer reflects every scan received more than five
minutes ago.

## Fit criterion

The 99th percentile of the delay between receiving a scan and serving an updated window
is under five minutes, measured weekly.
