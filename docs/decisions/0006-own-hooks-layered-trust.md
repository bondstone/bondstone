---
type: decision
id: ADR-0006
title: Ship minimal own hooks with a layered trust model
description: Bondstone ships its own git, Claude Code and CI hooks that keep agents from approving through supported paths and make any other change visible; spec-gates is optional.
status: proposed
---

# Ship minimal own hooks with a layered trust model

## Context and Problem Statement

Only a person may approve or verify; an agent that grades its own work makes every gate meaningless. Hooks cannot stop a determined agent with shell access, and the approval hash is not a signature. How does Bondstone enforce this, and what does it promise?

## Considered Options

- Bondstone's own minimal hooks (git pre-commit, Claude Code, CI), layered by release
- Depend on spec-gates for all enforcement
- No hooks; rely on the agent guide

## Decision Outcome

Chosen option: "Bondstone's own minimal hooks, layered by release", because it works without other tools, and it promises only what it can keep: agents cannot approve through supported paths, and any other change shows up in CI.

1. From 0.0, the pre-commit hook rejects staged changes to `status` or `verified` when `CLAUDE_CODE_CHILD_SESSION` is set.
2. From 0.2, `approve` and `verify` refuse to run in that environment or without a terminal. Claude Code hooks compare each edit's front-matter before and after, and a per-turn snapshot catches and restores changes made through the shell. The hooks block when they fail.
3. In CI, hashes are re-checked, and changes to approvals, packs, overrides or hook settings are reported as review signals.

spec-gates stays optional: a recipe shows how to run Bondstone as one of its gates.

### Consequences

- Good, because the claim matches what the hooks can actually do.
- Good, because the 0.0 block protects approvals from day one, before Claude Code hooks exist.
- Bad, because `CLAUDE_CODE_CHILD_SESSION` only identifies Claude Code; other agents are caught only by CI and review.
- Bad, because an agent with shell access can still write a valid `verified` record; the person must review it.
- Bad, because `hooks install` must merge into `.claude/settings.json` without overwriting other entries.
