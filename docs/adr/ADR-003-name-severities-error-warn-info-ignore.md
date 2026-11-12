---
id: ADR-003
type: adr:Decision
title: Name severities error, warn, info and ignore
status: accepted
owner: dworek
date: 2026-11-10
---

## Context

The POC switched a rule off with `{severity: off}`. YAML reads a bare `off` as the boolean
`false`, so the POC had to reject its own documented syntax or guess what a boolean meant
(D3 in [the design](../design.md)).

## Decision

A severity is one of `error`, `warn`, `info` and `ignore`. `error` fails the run, `warn` fails
it only with `--fail-on warn`, `info` is listed and never fails, and `ignore` disables the
rule. An override is the bare severity: `adr/alternatives-considered: warn`. A YAML boolean in
the place of a severity is a configuration error whose message names the fix.

## Alternatives considered

- **Keep `off` and read YAML `false` as off.** It accepts what people type, but `on`, `yes`
  and `true` would then need a meaning too, and none of them is obvious.

## Consequences

- No severity name collides with a YAML keyword.
- Profiles written for the POC need their `off` overrides renamed to `ignore`; the error
  message says so.
