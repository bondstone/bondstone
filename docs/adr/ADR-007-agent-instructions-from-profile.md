---
{id: ADR-007, title: Agent instructions are generated from the active profile, status: proposed,
  owner: dworek, date: '2026-11-10'}
---

## Context

Coding agents follow written instructions. Hand-written instructions about documentation rules drift from the rules themselves.

## Decision

`bondstone agent` generates instructions from the active profile: document types, links, statuses, rules (honouring overrides) and each pack's guidance.

## Alternatives considered

- Hand-maintained AGENTS.md sections: flexible, but drift from the rules.

## Consequences

Instructions change when the profile changes. Packs need an instructions file to give guidance beyond the rules.
