---
id: CAP-agent-instructions
title: Agent support
status: active
owner: dworek
code: AGT
depends_on: [CAP-profiles]
constrained_by: [ADR-007]
---

## Purpose

Give coding agents what they need to follow the documentation rules on their own.

## Requirements

### REQ-AGT-001: Generate instructions

`bondstone agent` SHALL generate instructions from the active profile: workflow, document types with locations, ids, fields, sections, statuses and links, roles, rules and each component's guidance.

#### Scenario: Instructions file

- Given a profile with adr
- When `bondstone agent --output AGENTS.bondstone.md` runs
- Then the file describes adr:Decision

### REQ-AGT-002: Explain rules

`bondstone explain RULE` SHALL show a rule's owner, effective severity, description and definition.

#### Scenario: Unknown rule

- Given no rule named nope
- When `bondstone explain nope` runs
- Then it exits with code 2

### REQ-AGT-003: Machine-readable results

`bondstone check --format json` SHALL output every diagnostic with rule, severity, message, path, line, node and hint, and a summary; the exit code SHALL be 1 when the check fails.

#### Scenario: Failing check

- Given a document with an unknown key
- When check runs with JSON output
- Then the JSON lists `bondstone/field-unknown` and the exit code is 1
