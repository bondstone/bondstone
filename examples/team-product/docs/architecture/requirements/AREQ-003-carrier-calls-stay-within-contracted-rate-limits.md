---
id: AREQ-003
title: Carrier calls stay within contracted rate limits
status: approved
owner: tracking-team
kind: constraint
priority: should
motivated_by: [PRIN-02]
---
## Statement

Calls to carrier APIs never exceed the rate agreed in each carrier contract.

## Fit criterion

No carrier returns a rate-limit response during a calendar month.
