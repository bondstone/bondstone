---
type: decision
id: ADR-0006
title: Ship minimal own hooks with a layered trust model
description: Only a person approves or verifies; Bondstone ships a small set of git, Claude Code and CI hooks to keep it that way, and a recipe for running as a spec-gates custom gate.
status: draft
---

# Ship minimal own hooks with a layered trust model

## Context and Problem Statement

An agent that can approve its own documents, or mark its own work verified, makes every gate meaningless. Checks must also hold at the agent, commit and merge boundaries. The spec-gates extension already enforces one policy identically at all three, with self-testing, protected files and commit-message rules. No hook can stop a determined agent with shell access, and the approval hash is not a signature. How does Bondstone keep approvals human, and what does it promise?

## Considered Options

- Trust agents to follow an instruction not to approve
- Build full enforcement into Bondstone
- Require spec-gates
- Ship minimal own hooks, layered by release, and a spec-gates recipe

## Decision Outcome

Chosen option: "Ship minimal own hooks, layered by release, and a spec-gates recipe", because it needs no other tool, and it promises only what hooks can keep: agents can't approve or verify through any supported path, and any other change shows up in review.

1. From 0.0, the pre-commit hook refuses staged changes to `status`, `verified` or `Verified:` lines when `CLAUDE_CODE_CHILD_SESSION` is set, as Claude Code does in the shells it runs.
2. From 0.2, `approve` and `verify` refuse to run without a terminal unless `--yes` is given, and always in an agent's shell. A Claude Code hook refuses agent calls to both commands, and edits that would change those fields.
3. In CI, from 0.1, every check runs again, and changes to approvals and hook settings show in the pull request's diff.

`bondstone hooks install --gates` prints the spec-gates policy entry; spec-gates is never a dependency.

### Consequences

- Good, because the 0.0 hook protects approvals from the first release, before Claude Code hooks exist.
- Good, because the small scope adds no heavy dependencies; teams that want stronger enforcement get it from spec-gates.
- Bad, because spec-gates policy can protect files but not refuse specific commands, so Bondstone keeps its own PreToolUse hook.
- Bad, because `CLAUDE_CODE_CHILD_SESSION` identifies only Claude Code; other agents, or an agent that writes a valid `verified` record with a script, are caught only in review.
