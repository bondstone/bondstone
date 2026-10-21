---
type: decision
id: ADR-0001
title: Build the CLI in Python with Typer and uv
description: Python 3.11+ with Typer, packaged and installed with uv, because it matches Spec Kit's ecosystem and starts fast enough for a pre-commit check.
status: proposed
---

# Build the CLI in Python with Typer and uv

## Context and Problem Statement

The CLI runs in every pre-commit hook, so `check --staged` must finish in under 1 s, start-up included. Its users already run Spec Kit, which is a Python tool installed with uv. Which language and toolchain should the CLI use?

## Considered Options

- Python 3.11+ with Typer and uv
- Go, shipped as a single binary
- Rust, shipped as a single binary
- Node.js with TypeScript

## Decision Outcome

Chosen option: "Python 3.11+ with Typer and uv", because Spec Kit users already have Python and uv, and its start-up fits the budget. Measured on 2026-10-21 (Linux, Python 3.12, warm cache): a Typer CLI starts in about 60 ms, and PyYAML's C loader reads 200 front-matters in about 8 ms.

### Consequences

- Good, because users install Bondstone with the same tool they use for Spec Kit (`uv tool install`).
- Good, because one language covers the CLI, the 0.0 stopgap script and the test plugin for console examples.
- Bad, because start-up depends on import discipline: commands import only what they use, and the hook path never loads Rich.
- Bad, because users need a Python interpreter, which a single binary would avoid.
- Revisit if the CI timing test on the 200-document fixture goes over 1 s.
