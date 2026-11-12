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

### REQ-AGT-003: Say what to read before editing

`bondstone context --for PATH...` SHALL list the nodes an edit of those files concerns: a
document among the paths, every node tagged in a file, the document of a tagged item, and the
nodes one link away from those documents in either direction. Each entry MUST say why it is
listed, and a document that is immutable in its current status MUST say so. A folder stands
for the files in it. `bondstone context --base REF` SHALL answer for the files changed since
REF instead, counts only the tags whose code region changed, and says for each node whether
its file changed.

#### Scenario: Code tagged for a requirement

- Given `reminders.dart` tagged with `REQ-REM-001`, whose capability is constrained by ADR-003
- When `bondstone context --for app/lib/reminders.dart` runs
- Then it lists the requirement, its capability and ADR-003, and marks ADR-003 as immutable

### REQ-AGT-004: Say which diff rules will fire

`bondstone context` SHALL list every diff rule that the given or changed files trigger, with
its effective severity, what each clause asks for, its hint, and for a traced clause the
documents that must change. A file that does not exist yet counts as added. A rule overridden
to `ignore` MUST be left out. When a rule can be exempted, the output names the trailer and
says to add one only when the user asks for it.

#### Scenario: Traced rule

- Given a rule that asks for an update of the living specs tagged in changed code
- When `bondstone context --for src/code.py` runs and that file is tagged for CAP-a
- Then the rule is listed with `must change: CAP-a`
