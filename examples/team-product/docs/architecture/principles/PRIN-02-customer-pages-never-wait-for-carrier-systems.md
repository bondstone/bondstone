---
id: PRIN-02
title: Customer pages never wait for carrier systems
status: approved
owner: tracking-team
---
## Statement

A page shown to a customer is served from our own data and never blocks on a carrier's API.

## Rationale

Carrier APIs are rate-limited and slow at the moments when customers check most often.

## Implications

- Carrier data is fetched ahead of time and stored.
- A carrier outage degrades freshness, not availability.
