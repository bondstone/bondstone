---
id: CLI-explain
title: explain
status: draft
synopsis: bondstone explain RULE
implements:
- CAP-agent-instructions
---

## Options

- `RULE`: qualified rule id, e.g. `adr/alternatives-considered`.

## Exit codes

- `0`: rule found.
- `2`: unknown rule.

## Examples

```sh
bondstone explain ost/committed-solution-has-evidence
```
