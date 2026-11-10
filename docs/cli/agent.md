---
id: CLI-agent
title: agent
status: draft
synopsis: bondstone agent [--output FILE]
implements:
- CAP-agent-instructions
---

## Options

- `--output FILE`: write to FILE (relative to the repository root) instead of standard output.

## Exit codes

- `0`: success.
- `2`: configuration or usage error.

## Examples

```sh
bondstone agent --output AGENTS.bondstone.md
```
