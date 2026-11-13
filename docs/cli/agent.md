---
id: CLI-agent
type: cli:Command
title: agent
status: stable
synopsis: bondstone agent [--format md|skill] [--output FILE]
implements: [CAP-agent-guidance]
---

Writes the instructions for coding agents from the active profile: the workflow, every type, every rule with its effective severity, and each component's guidance.

## Options

- `--root ROOT`: Repository root (default: the nearest folder with .bondstone/profile.yaml).
- `--format md|skill`: Markdown (default) or a Claude Code skill.
- `--output FILE`: Where to write (default: AGENTS.bondstone.md, or .claude/skills/bondstone/SKILL.md for a skill); `-` prints instead.

## Exit codes

- `0`: done
- `2`: the configuration is invalid
- `3`: no profile, or `--root` is not a directory

## Examples

```sh
bondstone agent
bondstone agent --format skill
bondstone agent --output -
```
