---
type: decision
id: ADR-0010
title: Ship the Spec Kit extension before the CLI
description: Release 0.0 ships the Spec Kit extension and preset with a stopgap behind their commands; the CLI replaces the stopgap in 0.1 and 0.2.
status: draft
---

# Ship the Spec Kit extension before the CLI

## Context and Problem Statement

The riskiest assumption is that agents follow the flow: start from `next`, stay on its step, name tests after requirement IDs and fill in `## Spec changes`. The design of 2026-10-10 built the CLI first and the Spec Kit integration last, in 0.2, so that assumption would first have been tested after about 22 focused days. Which part is built first?

## Considered Options

- The CLI first, the Spec Kit integration last
- The Spec Kit extension and preset first, with a stopgap behind their commands

## Decision Outcome

Chosen option: "The Spec Kit extension and preset first, with a stopgap behind their commands", because it tests whether agents follow the flow from the first week. Each command keeps its name from 0.0; only what runs behind it moves to the CLI, in 0.1 and 0.2, so nothing migrates. The stopgap computes statuses, the stage and the next step itself, in the CLI's formats, so the agent never computes a step. It is deleted in 0.2.

### Consequences

- Good, because agent behavior is measured from the first release, and each session's log says whether `next` was right.
- Good, because Bondstone's own repository follows its rules from release 0.0.
- Bad, because the stopgap duplicates part of the CLI's checks for two releases and must be deleted on time, and 0.0 grows from about 3 to about 5 focused days.
- Bad, because until 0.2 an approval is a bare `status: stable` without a hash (SPECKIT-12), so each approved document is approved again with `bondstone approve` in 0.2.
