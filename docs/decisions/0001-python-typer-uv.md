---
type: decision
id: ADR-0001
title: Build the CLI in Python with Typer and uv
description: Bondstone's CLI is written in Python 3.11 or later with Typer, and installed with uv.
status: proposed
---

# Build the CLI in Python with Typer and uv

## Context and Problem Statement

The CLI must start fast enough to run on every commit (`check --staged` under 1 s), edit YAML front-matter without losing comments or key order, install with one command, and fit the ecosystem of its first host, GitHub Spec Kit, whose own CLI is Python. Which language should it use?

## Considered Options

- Python 3.11+ with Typer, installed with uv
- TypeScript on Node.js
- Go, as a single static binary

## Decision Outcome

Chosen option: "Python 3.11+ with Typer, installed with uv", because Spec Kit users already have a Python toolchain, `ruamel.yaml` round-trips front-matter with its comments and key order, and a later Spec Kit workflow step could call Bondstone as a library. Start-up fits the budget: measured on 2026-10-21 (Linux, Python 3.12, warm cache), a Typer CLI starts in about 60 ms, and PyYAML's C loader reads 200 front-matters in about 8 ms.

### Consequences

- Good, because Bondstone shares one ecosystem with Spec Kit, and installs with `uv tool install bondstone`.
- Bad, because interpreter start-up eats into the pre-commit budget, so commands import lazily, the hook path never loads Rich, and hooks call the installed entry point, never `uvx`.
- Bad, because OpenSpec and BMAD users, who are mostly on Node.js, need Python installed.

### Confirmation

From 0.1, CI runs the 500-document benchmark (CHECK-10). If it goes over budget, this decision is revisited before more is built.
