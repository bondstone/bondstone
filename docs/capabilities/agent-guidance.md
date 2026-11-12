---
id: CAP-agent-guidance
type: capability:Capability
title: Guidance for agents
status: draft
owner: dworek
code: AGT
depends_on: [CAP-profiles, CAP-rules, CAP-graph]
---

## Purpose

An agent gets the documentation right on the first try when it can ask the repository what
the rules are before it writes anything. These commands answer from the same configuration
that `check` applies, so the answers and the gate cannot disagree.

## Requirements

### REQ-AGT-001: List the active rules with their effective severity

`bondstone rules` SHALL list every rule that can report in the repository: the rules that
packs, bridges and the profile declare, followed by the engine rules. Each rule MUST show the
severity that `check` applies, after the profile's overrides, and say when that differs from
the rule's default.

#### Scenario: Overridden rule

- Given a rule with the default severity `warn` and an override that sets it to `error`
- When `bondstone rules` runs
- Then the rule is listed as `error` with the note `default: warn`

### REQ-AGT-002: Explain one rule

`bondstone explain RULE` SHALL print what one rule asks and how to satisfy it: for a declared
rule its description, hint, selector and clauses and the manifest that declares it; for an
engine rule when it fires, why, and the fix. An unknown rule id MUST be refused with the
closest known ids.

#### Scenario: Misspelt rule id

- Given the engine rule `bondstone/immutable`
- When `bondstone explain bondstone/immutabel` runs
- Then it exits with 1 and suggests `bondstone/immutable`
