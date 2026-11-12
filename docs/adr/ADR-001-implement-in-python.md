---
id: ADR-001
type: adr:Decision
title: Implement bondstone in Python
status: accepted
owner: Adam Dworzyński
date: 2026-11-10
---

## Context

Bondstone v1 is a new codebase, so the implementation language was open (D1 in
[the design](../design.md)). The POC is a working Python engine. It proved the two libraries
the engine leans on, PyYAML and jsonschema. Spec Kit, the first tool bondstone integrates
with, is installed with the same toolchain.

## Decision

Bondstone is written in Python 3.11 or later and installed with `uv tool` or `pipx`. The
engine depends on PyYAML and jsonschema only.

## Alternatives considered

- **Go.** One static binary with no runtime to install, but weaker YAML and JSON Schema
  libraries, and nothing of the POC carries over.
- **TypeScript.** npm reaches BMAD users directly, but it has the same cost of starting again
  and gains nothing for Spec Kit users.

## Consequences

- Users need a Python toolchain; `uv tool install` hides most of it.
- Type schemas are JSON Schema, which pack authors can check with their own tools.
- Start-up time is that of a Python process, which is acceptable for a gate that runs once per
  commit or per agent turn.
