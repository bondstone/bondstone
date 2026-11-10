---
{id: ADR-003, title: Bridges own everything that connects packs, status: proposed,
  owner: dworek, date: '2026-11-10'}
---

## Context

Combining methods (for example discovery and architecture) needs cross-method links and hand-off rules. If packs reference each other, every combination couples them.

## Decision

Packs never reference other packs. Cross-pack link types, hand-off rules, cross-pack views and role assignments live in bridges, which declare the pack versions they require.

## Alternatives considered

- Inline connections in each profile: fast to start, impossible to reuse or test.
- Packs with optional dependencies on other packs: couples packs and multiplies versions.

## Consequences

Packs stay independent and reusable. Bridges are small, testable and versioned. A profile with packs that no bridge connects gets a warning.
