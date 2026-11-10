---
{id: ADR-005, title: The check is deterministic; quality review is separate, status: proposed,
  owner: dworek, date: '2026-11-10'}
---

## Context

Agents and CI need a gate that gives the same answer every time. Judging prose quality needs a language model, which does not.

## Decision

`bondstone check` only runs deterministic checks: structure, links, rules, code tags, views and git diffs. Any LLM-based review is a separate, non-blocking step.

## Alternatives considered

- Let an LLM judge documents in the gate: catches more, but flaky and expensive.

## Consequences

Failures are reproducible and explainable. Some quality problems (vague requirements) stay out of scope for the gate.
