---
id: CHG-004
title: CLI command documentation (self-hosting phase 2)
status: accepted
owner: dworek
kind: docs
---

## Why

The CLI is bondstone's public interface, and it is only described by `--help`. Self-hosting phase 2 (`docs/self-hosting.md`) documents every command and keeps those documents tied to the code.

## What changes

- Local pack `cli` (one `cli:Command` document per command, code-traceable with coverage error) and bridge `cli-capability`.
- A document for every command in `docs/cli/`, tagged in `cli.py`.
- A test that every parser command has a document.

## Out of scope

Generating `--help` text from the documents.
